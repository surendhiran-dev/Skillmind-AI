import requests

BASE_URL = 'http://127.0.0.1:5000'

def test_submit():
    # Login
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={"username": "admin", "password": "admin123"})
    if resp.status_code != 200:
        print("Login failed")
        return
    
    token = resp.json().get('token')
    headers = {"Authorization": f"Bearer {token}"}
    
    # Submit code
    code = "def two_sum(nums, target):\n    return [0, 1]"
    data = {"code": code, "problem_id": 4}
    
    resp = requests.post(f"{BASE_URL}/api/coding/submit", json=data, headers=headers)
    print(f"Status: {resp.status_code}")
    print(resp.json())

if __name__ == "__main__":
    test_submit()
