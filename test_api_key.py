
import os
import json
from openai import OpenAI
from dotenv import load_dotenv

# Ensure we're in the right directory for .env
os.chdir(os.path.dirname(os.path.abspath(__file__)))
load_dotenv('skill-mind-ai/backend/.env')

api_key = os.getenv('OPENAI_API_KEY')
print(f"Testing API Key: {api_key[:10]}...{api_key[-4:]}")

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=api_key,
)

try:
    print("Calling OpenRouter...")
    completion = client.chat.completions.create(
        model="openai/gpt-3.5-turbo",
        messages=[
            {
                "role": "user",
                "content": "Hello"
            }
        ],
        extra_headers={
            "HTTP-Referer": "http://localhost:5000",
            "X-OpenRouter-Title": "SkillMind AI Test",
        }
    )
    print("Success!")
    print(f"Response: {completion}")
    print(f"Content: {completion.choices[0].message.content}")
except Exception as e:
    print(f"Error Type: {type(e)}")
    print(f"Error: {e}")
    if hasattr(e, 'response'):
        print(f"Status Code: {e.response.status_code}")
        print(f"Response Text: {e.response.text}")
