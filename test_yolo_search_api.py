import requests

def test_yolo_search():
    query = "YOLO"
    url = f"http://127.0.0.1:8000/api/v1/papers/search?query={query}&threshold=0.1"
    print(f"Testing search for: '{query}' with threshold 0.1")
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        results = response.json()
        
        print(f"\nFound {len(results)} results:")
        for res in results:
            print(f"ID: {res['id']}, Score: {res['score']:.4f}, Title: {res['payload'].get('title')}")
            # print(f"Abstract Snippet: {res['payload'].get('abstract', '')[:200]}...")
            print("-" * 30)
            
    except Exception as e:
        print(f"Error calling API: {e}")

if __name__ == "__main__":
    test_yolo_search()
