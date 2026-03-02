import requests

def test_scoring():
    base_url = "http://localhost:5000"
    
    # 1. Login
    print("Logging in...")
    resp = requests.post(f"{base_url}/api/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    token = resp.json().get('token')
    if not token:
        print("Login failed")
        return
    
    headers = {"Authorization": f"Bearer {token}"}
    
    # 2. Get Stats
    print("Fetching stats...")
    resp = requests.get(f"{base_url}/api/dashboard/stats", headers=headers)
    data = resp.json()
    
    report = data.get('report')
    if report:
        print("\nReadiness Report:")
        print(f"Final Score: {report.get('final_score')}")
        marks = report.get('marks')
        if marks:
            print(f"Marks: Resume={marks.get('resume')}/10, Quiz={marks.get('quiz')}/30, Coding={marks.get('coding')}/30, Interview={marks.get('interview')}/30")
        else:
            print("ERROR: Marks not found in report")
    else:
        print("No report found. Need to generate one first.")
        
        # 3. Generate Report
        print("\nGenerating report...")
        resp = requests.post(f"{base_url}/api/scoring/generate-report", headers=headers)
        data = resp.json()
        print(f"Generated Final Score: {data.get('final_score')}")
        marks = data.get('marks')
        if marks:
             print(f"Marks: Resume={marks.get('resume')}/10, Quiz={marks.get('quiz')}/30, Coding={marks.get('coding')}/30, Interview={marks.get('interview')}/30")
        else:
            print("ERROR: Marks not found in generated report")

if __name__ == "__main__":
    test_scoring()
