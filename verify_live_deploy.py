import requests

def check_deployment():
    backend_url = "https://skillmind-ai.onrender.com"
    frontend_url = "https://skillmindai.netlify.app"
    
    print(f"Checking Backend: {backend_url}")
    try:
        r = requests.get(backend_url)
        print(f"Backend Root Status: {r.status_code}")
    except Exception as e:
        print(f"Backend Error: {e}")
        
    print(f"\nChecking Frontend: {frontend_url}")
    try:
        r = requests.get(frontend_url)
        print(f"Frontend Root Status: {r.status_code}")
    except Exception as e:
        print(f"Frontend Error: {e}")

    print("\nChecking API CORS (Simulating Preflight)...")
    try:
        headers = {
            'Origin': frontend_url,
            'Access-Control-Request-Method': 'POST',
            'Access-Control-Request-Headers': 'Content-Type'
        }
        r = requests.options(f"{backend_url}/api/auth/login", headers=headers)
        print(f"CORS Preflight Status: {r.status_code}")
        print(f"CORS Headers: {dict(r.headers)}")
        
        allow_origin = r.headers.get('Access-Control-Allow-Origin')
        if allow_origin == frontend_url or allow_origin == '*':
            print("✅ CORS is correctly configured!")
        else:
            print(f"❌ CORS error: Access-Control-Allow-Origin is '{allow_origin}'")
    except Exception as e:
        print(f"API Error: {e}")

if __name__ == "__main__":
    check_deployment()
