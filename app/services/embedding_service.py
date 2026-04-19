from sentence_transformers import SentenceTransformer
from typing import List
import os

class EmbeddingService:
    def __init__(self):
        # Resolve path relative to project root
        base_dir = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        local_path = os.path.join(base_dir, "models", "multi-qa-MiniLM-L6-cos-v1")

        if os.path.exists(local_path):
            print(f"Loading Multi-Vector Search Model (Local): {local_path}...")
            # local_files_only=True prevents the model from trying to connect to Hugging Face
            self.model = SentenceTransformer(local_path, local_files_only=True)
        else:
            print(f"Warning: Local model not found at {local_path}. Falling back to Hugging Face...")
            self.model = SentenceTransformer("multi-qa-MiniLM-L6-cos-v1")

    def get_embedding(self, text: str) -> List[float]:
        """
        Generates a 384-dimensional vector optimized for semantic search.
        Automatically handles pooling and normalization.
        """
        # We set normalize_embeddings=True to get 0.0 to 1.0 cosine similarity scores
        embedding = self.model.encode(text, normalize_embeddings=True)
        return embedding.tolist()


embedding_service = EmbeddingService()
