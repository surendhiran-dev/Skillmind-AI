import requests
import json

BASE_URL = 'http://127.0.0.1:5000/api'

def test_interview_flow():
    # 1. Start Interview
    print("Starting interview...")
    res = requests.post(f"{BASE_URL}/interview/start", json={"user_id": 2})
    if res.status_code != 200:
        print(f"FAILED to start: {res.status_code} - {res.text}")
        return
    
    data = res.json()
    token = data['token']
    question_text = data['response']['question']
    print(f"Interview started. Token: {token[:10]}...")
    print(f"ARIA: {question_text}")

    # 2. Submit Answer
    print("\nSubmitting answer...")
    answer_res = requests.post(f"{BASE_URL}/interview/answer", json={
        "token": token,
        "answer": "I am a proactive developer with experience in Python and React.",
        "question_text": question_text
    })
    
    print(f"Response Code: {answer_res.status_code}")
    try:
        print(f"Response Body: {json.dumps(answer_res.json(), indent=2)}")
    except:
        print(f"Response text: {answer_res.text}")

if __name__ == "__main__":
    test_interview_flow()
