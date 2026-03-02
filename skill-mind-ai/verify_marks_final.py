import urllib.request
import json

def test_scoring():
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
        
        if not token:
            print("Login failed")
            return
        
        headers = {"Authorization": f"Bearer {token}", 'Content-Type': 'application/json'}
        
        # 2. Get Stats
        print("Fetching stats...")
        req = urllib.request.Request(f"{base_url}/api/dashboard/stats", headers=headers)
        with urllib.request.urlopen(req) as f:
            data = json.loads(f.read().decode('utf-8'))
        
        report = data.get('report')
        if report:
            print("\nReadiness Report found:")
            print(f"Final Score: {report.get('final_score')}")
            marks = report.get('marks')
            if marks:
                print(f"Marks: Resume={marks.get('resume')}/10, Quiz={marks.get('quiz')}/30, Coding={marks.get('coding')}/30, Interview={marks.get('interview')}/30")
                print("Verification SUCCESS: Marks are present in dashboard stats.")
            else:
                print("ERROR: Marks not found in report")
        else:
            print("No report found in stats. Generating one...")
            req = urllib.request.Request(f"{base_url}/api/scoring/generate-report", headers=headers, method='POST')
            with urllib.request.urlopen(req) as f:
                data = json.loads(f.read().decode('utf-8'))
            
            print(f"Generated Final Score: {data.get('final_score')}")
            marks = data.get('marks')
            if marks:
                 print(f"Marks: Resume={marks.get('resume')}/10, Quiz={marks.get('quiz')}/30, Coding={marks.get('coding')}/30, Interview={marks.get('interview')}/30")
                 print("Verification SUCCESS: Marks are present in generate-report response.")
            else:
                print("ERROR: Marks not found in generated report")

    except Exception as e:
        print(f"Verification failed with error: {e}")

if __name__ == "__main__":
    test_scoring()
