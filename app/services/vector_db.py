from qdrant_client import QdrantClient
from qdrant_client.http import models
from app.core.config import settings
from typing import List, Dict, Any
from app.services.imrad_service import imrad_service

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
        Searches across all active vectors and takes the max similarity score per paper.
        If `section` is specified (e.g. 'methods'), only that vector is queried — 
        enabling precise section-targeted retrieval.
        """
        active_vectors = imrad_service.get_all_vector_names()

        # Section targeting: restrict to a single vector if a valid section is requested
        if section and section in active_vectors:
            print(f"[IMRAD] Section-targeted search using vector: '{section}'")
            active_vectors = [section]

        all_results = []
        for vector_name in active_vectors:
            try:
                response = self.client.query_points(
                    collection_name=self.collection_name,
                    using=vector_name,
                    query=vector,
                    query_filter=filter_obj,
                    limit=limit
                )
                all_results.extend(response.points)
            except Exception as e:
                # A vector may not exist for older papers — skip gracefully
                print(f"[IMRAD] Skipping vector '{vector_name}' (not found or error): {e}")

        # Merge: take max score per paper ID across all queried vectors
        merged: Dict[int, Any] = {}
        for hit in all_results:
            if hit.id not in merged or hit.score > merged[hit.id].score:
                merged[hit.id] = hit

        return sorted(merged.values(), key=lambda x: x.score, reverse=True)[:limit]

    def delete_paper(self, paper_id: int):
        self.client.delete(
            collection_name=self.collection_name,
            points_selector=models.PointIdsList(
                points=[paper_id]
            )
        )

    def recommend(self, paper_id: int, limit: int = 5, filter_obj: Any = None):
        """
        Finds papers similar to the given paper_id.
        Uses the 'methods' vector as the primary similarity signal for IMRAD-aware
        recommendations (most academically meaningful section for CS theses).
        Falls back to 'abstract' if 'methods' is unavailable.
        """
        # Prefer 'methods' section for recommendation (most content-rich for CS theses)
        recommend_vector = "methods" if "methods" in imrad_service.get_all_vector_names() else "abstract"
        try:
            results = self.client.query_points(
                collection_name=self.collection_name,
                using=recommend_vector,
                query=models.RecommendQuery(
                    recommend=models.RecommendInput(
                        positive=[paper_id]
                    )
                ),
                query_filter=filter_obj,
                limit=limit
            )
        except Exception:
            # Fallback to abstract if methods vector doesn't exist for this paper
            results = self.client.query_points(
                collection_name=self.collection_name,
                using="abstract",
                query=models.RecommendQuery(
                    recommend=models.RecommendInput(positive=[paper_id])
                ),
                query_filter=filter_obj,
                limit=limit
            )
        return results.points

vector_db = VectorDB()

