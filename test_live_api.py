import requests

def test_api():
    backend_url = "https://skillmind-ai.onrender.com"
    
    print("Testing POST /api/auth/send-otp...")
    try:
        # Sending dummy email to trigger error or success
        r = requests.post(f"{backend_url}/api/auth/send-otp", json={"email": "test@example.com"})
        print(f"Status: {r.status_code}")
        print(f"Response: {r.json()}")
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    test_api()
