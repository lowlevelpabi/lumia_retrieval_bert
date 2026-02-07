from app.services.embedding_service import embedding_service
from app.services.vector_db import vector_db
import numpy as np

def test_yolo_search():
    query = "YOLO"
    print(f"Testing search for: '{query}'")
    
    # Generate query vector
    query_vector = embedding_service.get_embedding(query)
    
    # 1. Search in Qdrant using search (RRF)
    print("\n--- Testing vector_db.search (RRF) ---")
    results_rrf = vector_db.search(query_vector)
    print(f"Found {len(results_rrf)} results:")
    for hit in results_rrf:
        print(f"ID: {hit.id}, Score: {hit.score:.4f}, Title: {hit.payload.get('title')}")
    
    # 2. Search in Qdrant using search_max
    print("\n--- Testing vector_db.search_max ---")
    results_max = vector_db.search_max(query_vector)
    print(f"Found {len(results_max)} results:")
    for hit in results_max:
        print(f"ID: {hit.id}, Score: {hit.score:.4f}, Title: {hit.payload.get('title')}")

if __name__ == "__main__":
    test_yolo_search()
