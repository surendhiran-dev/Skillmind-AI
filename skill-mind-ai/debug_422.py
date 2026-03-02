import requests

BASE_URL = "http://localhost:5000"

def debug_upload():
    # 1. Login to get token
    print("Logging in...")
    login_res = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    if login_res.status_code != 200:
        print(f"Login failed: {login_res.status_code} {login_res.text}")
        return
    
    token = login_res.json()['token']
    print(f"Login successful. Token: {token[:20]}...")

    # 2. Try upload
    print("Attempting upload...")
    file_content = b"This is a dummy resume content for testing."
    files = {'file': ('test_resume.txt', file_content, 'text/plain')}
    data = {'label': 'resume1'}
    headers = {'Authorization': f'Bearer {token}'}
    
    upload_res = requests.post(f"{BASE_URL}/api/resume/upload", 
                               files=files, 
                               data=data, 
                               headers=headers)
    
    print(f"Upload Result: {upload_res.status_code}")
    print(f"Response Body: {upload_res.text}")

if __name__ == "__main__":
    debug_upload()
