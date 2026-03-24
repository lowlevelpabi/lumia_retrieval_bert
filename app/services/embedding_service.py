from sentence_transformers import SentenceTransformer
from typing import List
import os

model = SentenceTransformer("multi-qa-MiniLM-L6-cos-v1")
model.save("./models/multi-qa-MiniLM-L6-cos-v1")

class EmbeddingService:
    def __init__(self):
        local_path = "./models/multi-qa-MiniLM-L6-cos-v1"
        model_name = local_path if os.path.exists(local_path) else "multi-qa-MiniLM-cos-v1"

        print(f"Loading Multi-Vector Search Model: {model_name}...")

        self.model = SentenceTransformer(model_name)

    def get_embedding(self, text: str) -> List[float]:
        """
        Generates a 384-dimensional vector optimized for semantic search.
        Automatically handles pooling and normalization.
        """
        # We set normalize_embeddings=True to get 0.0 to 1.0 cosine similarity scores
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()


embedding_service = EmbeddingService()
