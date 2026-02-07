import requests
import json

BASE_URL = "http://127.0.0.1:8000/api/v1"

def test_auth():
    print("\n--- Testing Authentication ---")
    
    # 1. Register Admin
    reg_data = {
        "username": "admin_test",
        "email": "admin@test.com",
        "password": "password123",
        "role": "Admin"
    }
    resp = requests.post(f"{BASE_URL}/auth/register", json=reg_data)
    print(f"Register Admin: {resp.status_code}")
    if resp.status_code == 500:
        print(f"Error: {resp.text}")

    # 2. Login Admin
    login_data = {
        "username": "admin_test",
        "password": "password123"
    }
    resp = requests.post(f"{BASE_URL}/auth/login", data=login_data)
    token = resp.json().get("access_token")
    print(f"Login Admin: {'Success' if token else 'Failed'}")
    return token

def test_filtering(token):
    print("\n--- Testing Advanced Filtering ---")
    headers = {"Authorization": f"Bearer {token}"}
    
    # 1. Search with Year filter
    resp = requests.get(f"{BASE_URL}/papers/search?query=YOLO&year=2024", headers=headers)
    print(f"Search (Year=2024): {len(resp.json())} results")

    # 2. Search with Department filter
    resp = requests.get(f"{BASE_URL}/papers/search?query=YOLO&department=College of Computer Science", headers=headers)
    print(f"Search (Dept=CCS): {len(resp.json())} results")

def test_rbac(admin_token):
    print("\n--- Testing Role-Based Access Control ---")
    
    # 1. Register a regular User
    reg_data = {
        "username": "user_test",
        "email": "user@test.com",
        "password": "password123",
        "role": "User"
    }
    requests.post(f"{BASE_URL}/auth/register", json=reg_data)
    
    # 2. Login User
    login_data = {"username": "user_test", "password": "password123"}
    resp = requests.post(f"{BASE_URL}/auth/login", data=login_data)
    user_token = resp.json().get("access_token")
    
    user_headers = {"Authorization": f"Bearer {user_token}"}
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    # 3. User tries to delete (Should FAIL - 403)
    resp = requests.delete(f"{BASE_URL}/papers/1", headers=user_headers)
    print(f"User Delete (Expected 403): {resp.status_code}")

    # 4. Admin tries to delete (Should PASS - 404/200 depend on ID)
    resp = requests.delete(f"{BASE_URL}/papers/999", headers=admin_headers)
    print(f"Admin Delete Non-existent (Expected 404): {resp.status_code}")

if __name__ == "__main__":
    try:
        token = test_auth()
        if token:
            test_filtering(token)
            test_rbac(token)
    except Exception as e:
        print(f"Test failed: {e}")
