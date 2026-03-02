import requests

BASE_URL = "http://localhost:5000"

def test_compare():
    # 1. Login
    print("Logging in...")
    login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    token = login_res.json()['token']
    headers = {'Authorization': f'Bearer {token}'}

    # 2. Upload a dummy resume first
    print("Uploading resume...")
    files = {'file': ('resume.txt', b"I am a developer with experience in Python and Flask.", 'text/plain')}
    requests.post(f"{BASE_URL}/api/resume/upload", files=files, headers=headers, data={'label': 'resume1'})

    # 3. Test Compare
    print("Testing Compare & Sync...")
    jd_payload = {"jd": "Looking for a Python developer with knowledge of SQL."}
    compare_res = requests.post(f"{BASE_URL}/api/resume/compare", json=jd_payload, headers=headers)
    
    print(f"Status: {compare_res.status_code}")
    print(f"Response: {compare_res.json()}")

if __name__ == "__main__":
    test_compare()
