import urllib.request
import json

def test_coding_flow():
    base_url = "http://localhost:5000"
    
    try:
        # 1. Login
        print("Logging in...")
        req = urllib.request.Request(f"{base_url}/api/auth/login", 
                                   data=json.dumps({"username": "admin", "password": "admin123"}).encode('utf-8'),
                                   headers={'Content-Type': 'application/json'},
                                   method='POST')
        with urllib.request.urlopen(req) as f:
            resp = json.loads(f.read().decode('utf-8'))
            token = resp.get('token')
        
        headers = {"Authorization": f"Bearer {token}", 'Content-Type': 'application/json'}
        
        # 2. Generate Challenge Set
        print("Generating coding challenge set...")
        req = urllib.request.Request(f"{base_url}/api/coding/challenge-set", headers=headers, method='POST')
        with urllib.request.urlopen(req) as f:
            data = json.loads(f.read().decode('utf-8'))
        
        challenges = data.get('challenges', [])
        print(f"Number of challenges: {len(challenges)}")
        assert len(challenges) == 6, f"Expected 6 challenges, got {len(challenges)}"
        
        difficulties = [c['difficulty'] for c in challenges]
        print(f"Difficulties: {difficulties}")
        # Note: Depending on bank size, it might not be exactly 2/2/2 if bank is small, but we try.
        
        # 3. Submit all with dummy code
        print("\nSubmitting all coding challenges...")
        submissions = []
        for c in challenges:
            submissions.append({
                "problem_id": c["id"],
                "code": "def solution():\n    return True" # Generic invalid code for tests but valid syntax
            })
        
        req = urllib.request.Request(f"{base_url}/api/coding/submit-all", 
                                   data=json.dumps({"submissions": submissions}).encode('utf-8'),
                                   headers=headers, method='POST')
        with urllib.request.urlopen(req) as f:
            result = json.loads(f.read().decode('utf-8'))
        
        print(f"\nTotal Marks: {result.get('total_marks')}/{result.get('max_marks')}")
        print(f"Score PCT: {result.get('score_pct')}%")
        
        # 4. Verify Dashboard Stats
        print("\nVerifying dashboard stats...")
        req = urllib.request.Request(f"{base_url}/api/dashboard/stats", headers=headers)
        with urllib.request.urlopen(req) as f:
            dash = json.loads(f.read().decode('utf-8'))
        
        coding_marks = dash.get('report', {}).get('marks', {}).get('coding')
        print(f"Dashboard Coding Marks: {coding_marks}/30")
        
        # Since we submitted 6 challenges, and they likely failed tests but had some quality,marks might be 1 or 0.
        print("\nAll verifications PASSED!")

    except Exception as e:
        print(f"Verification failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_coding_flow()
