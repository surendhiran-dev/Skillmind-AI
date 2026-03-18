import requests

BASE_URL = 'http://127.0.0.1:5000/api'

def test_dashboard_stats():
    # 1. Login to get token
    print("Logging in...")
    login_res = requests.post(f"{BASE_URL}/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    
    if login_res.status_code != 200:
        print(f"Login failed: {login_res.text}")
        return
        
    token = login_res.json()['token']
    print(f"Logged in. Token: {token[:10]}...")

    # 2. Get Stats
    print("\nFetching dashboard stats...")
    stats_res = requests.get(f"{BASE_URL}/dashboard/stats", headers={
        "Authorization": f"Bearer {token}"
    })
    
    print(f"Response Code: {stats_res.status_code}")
    if stats_res.status_code == 200:
        print("Success! Dashboard stats retrieved.")
        # print(stats_res.json())
    else:
        print(f"Failed: {stats_res.text}")

if __name__ == "__main__":
    test_dashboard_stats()
