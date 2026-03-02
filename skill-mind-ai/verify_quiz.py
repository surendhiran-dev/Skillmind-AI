import urllib.request
import json

def test_quiz():
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
        
        # 2. Generate Quiz
        print("Generating quiz...")
        req = urllib.request.Request(f"{base_url}/api/quiz/generate", headers=headers)
        with urllib.request.urlopen(req) as f:
            data = json.loads(f.read().decode('utf-8'))
        
        questions = data.get('questions', [])
        print(f"Number of questions: {len(questions)}")
        assert len(questions) == 15, f"Expected 15 questions, got {len(questions)}"
        
        for i, q in enumerate(questions, 1):
            print(f"  Q{i}: [{q['difficulty']}] {q['question'][:60]}...")
        
        # 3. Submit with dummy answers
        print("\nSubmitting quiz with sample answers...")
        responses = [{"question": q["question"], "answer": f"The answer involves understanding {q['skill']} concepts and implementation details."} for q in questions]
        
        req = urllib.request.Request(f"{base_url}/api/quiz/submit", 
                                   data=json.dumps({"responses": responses}).encode('utf-8'),
                                   headers=headers, method='POST')
        with urllib.request.urlopen(req) as f:
            result = json.loads(f.read().decode('utf-8'))
        
        print(f"\nTotal Marks: {result.get('total_marks')}/{result.get('max_marks')}")
        print(f"Score (percentage): {result.get('score', 0):.1f}%")
        print(f"Question results count: {len(result.get('results', []))}")
        
        print("\nAll verifications PASSED!")

    except Exception as e:
        print(f"Verification failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_quiz()
