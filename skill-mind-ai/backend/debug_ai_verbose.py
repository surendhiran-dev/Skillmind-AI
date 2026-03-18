import os
import sys
import logging
from dotenv import load_dotenv

# Configure logging to see errors
logging.basicConfig(level=logging.INFO)

# Add the backend directory to sys.path to import app modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.ai_service import call_ai, configure_ai, HAS_AI, MODULE_CONFIGS

def debug_test():
    load_dotenv()
    print(f"--- AI SERVICE DEBUG ---")
    print(f"CWD: {os.getcwd()}")
    
    # Check .env directly
    with open(".env", "r") as f:
        env_lines = f.readlines()
        for line in env_lines:
            if "KEY" in line:
                key_name = line.split("=")[0]
                val = line.split("=")[1].strip()
                print(f"Env {key_name}: {val[:15]}...{val[-5:]}")

    configure_ai()
    
    print(f"\nGlobal HAS_AI: {HAS_AI}")
    for mod in ['default', 'interview', 'resume', 'quiz', 'coding']:
        config = MODULE_CONFIGS[mod]
        print(f"Module '{mod}':")
        print(f"  Model: {config['model']}")
        print(f"  Has Client: {config['client'] is not None}")
        print(f"  Has OpenRouter: {config['has_or']}")
        print(f"  Has Anthropic: {config['has_anthropic']}")

    print("\nExecuting Test Call (Interview Module)...")
    try:
        response = call_ai("Say 'Test Successful'", module='interview')
        print(f"Response: {response}")
    except Exception as e:
        print(f"Caught Exception: {e}")

if __name__ == "__main__":
    debug_test()
