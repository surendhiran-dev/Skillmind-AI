import requests
import json

BASE_URL = "http://localhost:5000"

def get_token():
    # Attempt to login or get existing user
    res = requests.post(f"{BASE_URL}/api/auth/login", json={
        "username": "suren", # Assuming this user exists or I can register
        "password": "password"
    })
    if res.status_code == 200:
        return res.json().get('token')
    return None

def trigger_500():
    token = get_token()
    if not token:
        print("Could not get token")
        return

    headers = {"Authorization": f"Bearer {token}"}
    
    # Simulate the LFU Cache submission
    code = """
from collections import defaultdict, OrderedDict
from typing import List, Dict

class LFUCache:
    def __init__(self, capacity: int):
        self.capacity = capacity
    
    def get(self, key: int) -> int:
        return -1
"""
    # Assuming problem_id 31 was the LFU one from before if it was AI generated
    # Or I can just try a common ID
    payload = {
        "code": code,
        "problem_id": 31, 
        "language": "python"
    }
    
    res = requests.post(f"{BASE_URL}/api/coding/submit", json=payload, headers=headers)
    print(f"Status Code: {res.status_code}")
    print(f"Response: {res.text}")

if __name__ == "__main__":
    trigger_500()
