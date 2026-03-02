import requests
import json

BASE_URL = 'http://127.0.0.1:5000'

def test_submit_all():
    # Login
    resp = requests.post(f"{BASE_URL}/api/auth/login", json={"username": "admin", "password": "admin123"})
    if resp.status_code != 200:
        print("Login failed")
        return
    
    token = resp.json().get('token')
    headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}
    
    # Simulate 6 submissions
    submissions = []
    for i in range(1, 7):
        submissions.append({
            "problem_id": i,
            "code": f"def solve_{i}():\n    return True"
        })
    
    data = {"submissions": submissions}
    
    print("Submitting all challenges...")
    try:
        resp = requests.post(f"{BASE_URL}/api/coding/submit-all", json=data, headers=headers)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            result = resp.json()
            print(f"Total Marks: {result['total_marks']}/30")
            print(f"Score Percentage: {result['score_pct']}%")
            print(f"Number of results: {len(result['results'])}")
        else:
            print(f"Error: {resp.text}")
    except Exception as e:
        print(f"Exception: {e}")

if __name__ == "__main__":
    test_submit_all()
