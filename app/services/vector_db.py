from qdrant_client import QdrantClient
from qdrant_client import models
from app.core.config import settings
from typing import List, Dict, Any
from app.services.imrad_service import imrad_service

# ── IMRAD Section Weights ─────────────────────────────────────────────────────
# Title/abstract are strong signals; body sections weighted by research value.
# These multiply the raw cosine score before the max-merge step so that a
# high-scoring title hit outranks a moderate methods hit.
SECTION_WEIGHTS: Dict[str, float] = {
    "title":        1.50,
    "abstract":     1.30,
    "methods":      1.20,
    "results":      1.10,
    "introduction": 0.90,
    "discussion":   0.90,
}

# Recommendation section weights:
# Methods + Results carry the most academic signal ("what was done" and "what was found").
# Abstract/Title are strong anchors. Introduction/Discussion provide softer thematic context.
RECOMMEND_WEIGHTS: Dict[str, float] = {
    "methods":      1.60,   # highest — technical approach alignment
    "results":      1.60,   # highest — empirical findings alignment
    "abstract":     1.30,   # strong anchor — paper summary
    "title":        1.20,   # good anchor — topical label
    "introduction": 0.90,   # softer — background context
    "discussion":   0.90,   # softer — interpretive context
}

class VectorDB:
    def __init__(self):
        self.client = QdrantClient(path=settings.QDRANT_PATH)
        self.collection_name = settings.COLLECTION_NAME
        self._ensure_collection()

    def _ensure_collection(self):
        # Check if collection exists and has named vectors support
        try:
            info = self.client.get_collection(self.collection_name)
            # Check if it's already using named vectors by checking the type of 'vectors'
            if not hasattr(info.config.params.vectors, 'title'):
                print("⚠️ Collection exists but doesn't support named vectors. Force recreating...")
                self.client.delete_collection(self.collection_name)
                raise Exception("Need named vectors")
        except Exception as e:
            print(f"Initialing IMRAD Multi-Vector collection '{self.collection_name}'...")
            self.client.recreate_collection(
                collection_name=self.collection_name,
                vectors_config=imrad_service.get_qdrant_vector_config(),
            )

    def upsert_paper(self, paper_id: int, vectors: Dict[str, List[float]], metadata: Dict[str, Any]):
        self.client.upsert(
            collection_name=self.collection_name,
            points=[
                models.PointStruct(
                    id=paper_id,
                    vector=vectors,  # Accepting a dict of vectors
                    payload=metadata
                )
            ]
        )

    def search(self, vector: List[float], limit: int = 5):
        # Dynamically build prefetch list from all active vector names (IMRAD + title + abstract if enabled)
        active_vectors = imrad_service.get_all_vector_names()
        results = self.client.query_points(
            collection_name=self.collection_name,
            prefetch=[
                models.Prefetch(query=vector, using=name, limit=limit)
                for name in active_vectors
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF),  # Reciprocal Rank Fusion for best relevance
            limit=limit
        )
        return results.points

    def search_max(self, vector: List[float], limit: int = 5, filter_obj: Any = None, section: str = None):
        """
        Searches across all active vectors with IMRAD section weighting.

        Each section's cosine score is multiplied by a pre-defined weight
        (see SECTION_WEIGHTS) so that a strong title/abstract hit outranks
        a moderate body-section hit.  The highest *weighted* score per paper
        is kept and results are sorted descending.

        If `section` is specified (e.g. 'methods'), only that vector is
        queried — enabling precise section-targeted retrieval; weighting
        still applies for consistency.
        """
        active_vectors = imrad_service.get_all_vector_names()

        # Section targeting: restrict to a single vector if a valid section is requested
        if section and section in active_vectors:
            print(f"[IMRAD] Section-targeted search using vector: '{section}'")
            active_vectors = [section]

        all_results = []  # list of (weighted_score, hit)
        for vector_name in active_vectors:
            weight = SECTION_WEIGHTS.get(vector_name, 1.0)
            try:
                response = self.client.query_points(
                    collection_name=self.collection_name,
                    using=vector_name,
                    query=vector,
                    query_filter=filter_obj,
                    limit=limit
                )
                for hit in response.points:
                    # Keep raw score for the UI, but record weighted score for ranking
                    all_results.append({
                        "weighted_score": hit.score * weight,
                        "raw_hit": hit
                    })
            except Exception as e:
                print(f"[IMRAD] Skipping vector '{vector_name}' (not found or error): {e}")

        # Merge: take max *weighted* score per paper ID, but keep the original raw hit.score
        merged: Dict[int, Any] = {}
        # Track the best weighted score for each paper
        best_weighted: Dict[int, float] = {}

        for item in all_results:
            hid = item["raw_hit"].id
            wscore = item["weighted_score"]
            if hid not in best_weighted or wscore > best_weighted[hid]:
                best_weighted[hid] = wscore
                # Ensure the hit.score is capped at 1.0 (some metrics can exceed slightly)
                item["raw_hit"].score = min(1.0, item["raw_hit"].score)
                merged[hid] = item["raw_hit"]

        # Sort by the weighted score, returning the raw hit
        sorted_hits = sorted(merged.keys(), key=lambda hid: best_weighted[hid], reverse=True)
        return [merged[hid] for hid in sorted_hits][:limit]

    def delete_paper(self, paper_id: int):
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.PointIdsList(
                points=[paper_id]
            )
        )

    def recommend(
        self,
        paper_id: int,
        limit: int = 15,
        filter_obj: Any = None,
        source_texts: Dict[str, str] = None,
    ):
        """
        Context-Aware Multi-Section Recommendation.

        Instead of using Qdrant's built-in RecommendInput (which only does geometric
        vector neighborhood), this method:

        1. Accepts the source paper's actual section texts (methods, results, abstract,
           title, introduction, discussion) passed from the API layer.
        2. Embeds each available section into a fresh query vector using the same
           SentenceTransformer model used at upload time.
        3. Runs a weighted semantic search per section across the entire corpus
           (excluding the source paper itself via filter_obj).
        4. Merges results using per-section RECOMMEND_WEIGHTS so that strong
           methodology/results alignment outranks vague topical similarity.

        This means recommendations are driven by the MEANING of what the paper
        actually says, not just its position in Qdrant's vector space.
        """
        from app.services.embedding_service import embedding_service

        active_vectors = imrad_service.get_all_vector_names()

        # If no source texts provided, fall back to title-only search (safe default)
        if not source_texts:
            source_texts = {}

        all_results: List[Dict] = []  # list of {weighted_score, raw_hit, match_section}

        for vector_name in active_vectors:
            weight = RECOMMEND_WEIGHTS.get(vector_name, 1.0)

            # Resolve the section text to embed for this vector slot.
            # Priority: exact section name → fallback to abstract → skip if nothing.
            text_to_embed = (
                source_texts.get(vector_name)
                or source_texts.get("abstract")
                or source_texts.get("title")
                or ""
            ).strip()

            if not text_to_embed:
                print(f"[Recommend] Skipping vector '{vector_name}' — no source text available.")
                continue

            try:
                # Embed the source paper's actual section text as a live query vector
                query_vector = embedding_service.get_embedding(text_to_embed)

                response = self.client.query_points(
                    collection_name=self.collection_name,
                    using=vector_name,
                    query=query_vector,
                    query_filter=filter_obj,
                    limit=limit * 3,  # generous pool for cross-encoder re-ranking later
                )
                for hit in response.points:
                    # Exclude the source paper itself
                    if int(hit.id) == int(paper_id):
                        continue
                    all_results.append({
                        "weighted_score": hit.score * weight,
                        "raw_hit": hit,
                        "match_section": vector_name,
                    })
            except Exception as e:
                print(f"[Recommend] Skipping vector '{vector_name}' (error): {e}")
                continue

        # Max-merge: keep the best weighted score per paper ID
        merged: Dict[int, Any] = {}
        best_weighted: Dict[int, float] = {}
        best_section: Dict[int, str] = {}

        for item in all_results:
            hit = item["raw_hit"]
            wscore = item["weighted_score"]
            hid_int = int(hit.id)

            if hid_int not in best_weighted or wscore > best_weighted[hid_int]:
                best_weighted[hid_int] = wscore
                best_section[hid_int] = item["match_section"]
                hit.score = min(1.0, hit.score)  # cap raw cosine at 1.0
                merged[hid_int] = hit

        # Annotate each merged hit with the section that drove its best score
        for hid_int, hit in merged.items():
            hit.payload["_match_section"] = best_section.get(hid_int, "abstract")

        sorted_ids = sorted(merged.keys(), key=lambda x: best_weighted[x], reverse=True)
        return [merged[hid] for hid in sorted_ids][:limit]

vector_db = VectorDB()
