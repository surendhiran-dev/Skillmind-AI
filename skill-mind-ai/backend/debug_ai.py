import os
import sys
from dotenv import load_dotenv

# Add the backend directory to sys.path to import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.ai_service import call_ai, configure_ai, HAS_AI, MODULE_CONFIGS

def debug_test():
    load_dotenv()
    print(f"Current Working Directory: {os.getcwd()}")
    print(f"INTERVIEW_AI_KEY: {os.getenv('INTERVIEW_AI_KEY')[:15]}...")
    
    # Re-configure to ensure latest .env is used
    configure_ai()
    
    print(f"Has AI: {HAS_AI}")
    print(f"Interview Model: {MODULE_CONFIGS['interview']['model']}")
    print(f"Has Client: {MODULE_CONFIGS['interview']['client'] is not None}")
    
    if not HAS_AI:
        print("Error: AI is not initialized. Check your .env file and key format.")
        return

    print("\nTesting call_ai for 'default' module...")
    response = call_ai("Hello, respond with 'Success' if you can hear me.", module='default')
    print(f"Default Module Response: {response}")

    print("\nTesting call_ai for 'interview' module...")
    response = call_ai("Hello, respond with 'Interview Success' if you can hear me.", module='interview')
    print(f"Interview Module Response: {response}")

if __name__ == "__main__":
    debug_test()
