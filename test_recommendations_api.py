import requests

def test_recommendations():
    paper_id = 2  # The YOLO paper
    url = f"http://127.0.0.1:8000/api/v1/papers/{paper_id}/recommendations?limit=5"
    print(f"Testing recommendations for Paper ID: {paper_id}")
    
    try:
        response = requests.get(url)
        response.raise_for_status()
        results = response.json()
        
        print(f"\nFound {len(results)} recommendations:")
        for res in results:
            print(f"ID: {res['id']}, Score: {res['score']:.4f}, Title: {res['payload'].get('title')}")
            print("-" * 30)
            
    except Exception as e:
        print(f"Error calling API: {e}")

if __name__ == "__main__":
    test_recommendations()
