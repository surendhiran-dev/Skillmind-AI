import os
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()
api_key = os.getenv("GOOGLE_API_KEY")
print(f"API Key found: {api_key[:5]}...{api_key[-5:] if api_key else 'None'}")

if not api_key:
    print("No API key found!")
    exit(1)

genai.configure(api_key=api_key)
try:
    model = genai.GenerativeModel("gemini-1.5-flash")
    response = model.generate_content("Say hello")
    print(f"Response: {response.text}")
except Exception as e:
    print(f"Error: {e}")
