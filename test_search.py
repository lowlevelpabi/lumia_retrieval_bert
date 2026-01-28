from app.services.embedding_service import embedding_service
from app.services.vector_db import vector_db
import numpy as np

def test_search():
    query = "deep learning"
    print(f"Testing search for: '{query}'")
    
    # Generate query vector
    query_vector = embedding_service.get_embedding(query)
    
    # Search in Qdrant
    results = vector_db.search(query_vector)
    
    print(f"\nFound {len(results)} results:")
    for hit in results:
        print(f"ID: {hit.id}, Score: {hit.score:.4f}, Title: {hit.payload.get('title')}")

if __name__ == "__main__":
    test_search()
