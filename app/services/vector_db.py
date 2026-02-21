from qdrant_client import QdrantClient
from qdrant_client.http import models
from app.core.config import settings
from typing import List, Dict, Any

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
            print(f"Initialing Multi-Vector collection '{self.collection_name}'...")
            self.client.recreate_collection(
                collection_name=self.collection_name,
                vectors_config={
                    "title": models.VectorParams(size=384, distance=models.Distance.COSINE),
                    "abstract": models.VectorParams(size=384, distance=models.Distance.COSINE),
                },
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
        # We query BOTH the title and abstract vectors and take the best score
        # Using the query interface for better results
        results = self.client.query_points(
            collection_name=self.collection_name,
            prefetch=[
                models.Prefetch(query=vector, using="title", limit=limit),
                models.Prefetch(query=vector, using="abstract", limit=limit),
            ],
            query=models.FusionQuery(fusion=models.Fusion.RRF), # Reciprocal Rank Fusion for best relevance
            limit=limit
        )
        return results.points

    def search_max(self, vector: List[float], limit: int = 5, filter_obj: Any = None):
        """Alternative search that simply takes the max similarity across both vectors"""
        # Query title
        title_response = self.client.query_points(
            collection_name=self.collection_name,
            using="title",
            query=vector,
            query_filter=filter_obj,
            limit=limit
        )
        title_results = title_response.points

        # Query abstract
        abstract_response = self.client.query_points(
            collection_name=self.collection_name,
            using="abstract",
            query=vector,
            query_filter=filter_obj,
            limit=limit
        )
        abstract_results = abstract_response.points
        
        # Merge and take max score per ID
        merged = {}
        for hit in title_results + abstract_results:
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
        Finds papers similar to the given paper_id based on their abstract embeddings.
        Uses Qdrant's Recommend API with optional metadata filtering.
        """
        results = self.client.query_points(
            collection_name=self.collection_name,
            using="abstract",
            query=models.RecommendQuery(
                recommend=models.RecommendInput(
                    positive=[paper_id]
                )
            ),
            query_filter=filter_obj,
            limit=limit
        )
        return results.points

vector_db = VectorDB()

