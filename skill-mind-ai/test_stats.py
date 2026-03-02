import requests

BASE_URL = "http://localhost:5000"

def test_stats():
    # 1. Login
    print("Logging in...")
    login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    token = login_res.json()['token']
    headers = {'Authorization': f'Bearer {token}'}

    # 2. Test Stats
    print("Testing Dashboard Stats...")
    stats_res = requests.get(f"{BASE_URL}/api/dashboard/stats", headers=headers)
    
    print(f"Status: {stats_res.status_code}")
    print(f"Response: {stats_res.json()}")

if __name__ == "__main__":
    test_stats()
