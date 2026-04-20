import os
import sys
from unittest.mock import MagicMock

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'skill-mind-ai', 'backend'))

from app import create_app
from app.services.coding_service import get_challenge_set
from app.models.models import db

def verify_6_questions():
    app = create_app()
    with app.app_context():
        print("Testing get_challenge_set for consistency...")
        
        # Test 5 times
        for i in range(1, 6):
            print(f"Run {i}: Calling get_challenge_set...")
            res = get_challenge_set(jd_text="Senior Python Developer", resume_data={"user_id": 1, "skills": ["Python", "Flask"]})
            challenges = res["challenges"]
            count = len(challenges)
            print(f"Run {i}: Received {count} challenges.")
            
            if count != 6:
                print(f"FAILED: Expected 6 questions, got {count}")
                # We won't exit here as it might be an AI variance, but it should be 6 with retry logic
            else:
                print(f"SUCCESS: Received exactly 6 questions.")

if __name__ == "__main__":
    verify_6_questions()
