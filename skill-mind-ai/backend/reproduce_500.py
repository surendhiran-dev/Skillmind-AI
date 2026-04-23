import os
import sys
import json
import traceback

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.models.models import AIChallenge, User
from app.services.coding_service import run_test_cases, evaluate_code_quality, get_ai_coding_analysis, calculate_comprehensive_score

def reproduce_500():
    app = create_app()
    with app.app_context():
        print("\n--- Diagnostic: Simulating Coding Submission ---")
        
        # 1. Setup Mock Environment
        user = User.query.first()
        if not user:
            print("No users found in database.")
            return
            
        challenge = AIChallenge.query.first()
        if not challenge:
            print("No challenges found in database.")
            return

        code = "def " + challenge.title.lower().replace(' ', '_') + "(input):\n    return []"
        problem_id = challenge.id
        language = 'python'
        
        print(f"User: {user.username}")
        print(f"Problem: {challenge.title} (ID: {problem_id})")
        print(f"Submitted Code:\n{code}")

        # 2. Replicate Route Logic
        try:
            print("\n[Step 1] Running Test Cases...")
            test_results, test_score, exec_time = run_test_cases(code, problem_id, language)
            print(f"Status: OK, Test Score: {test_score}")

            print("\n[Step 2] Evaluating Quality...")
            quality = evaluate_code_quality(code, language, problem_title=challenge.title)
            print(f"Status: OK, Quality Score: {quality.get('score', 0)}")

            print("\n[Step 3] Generating AI Analysis...")
            challenge_dict = {
                "id": challenge.id,
                "title": challenge.title,
                "description": challenge.description,
                "language": challenge.language,
                "test_cases": challenge.test_cases,
                "test_wrapper": challenge.test_wrapper
            }
            ai_analysis = get_ai_coding_analysis(code, language, challenge_dict, test_results)
            print("Status: OK")

            print("\n[Step 4] Calculating Comprehensive Score...")
            final_score = calculate_comprehensive_score(test_score, quality, ai_analysis)
            print(f"Status: OK, Final Score: {final_score}")

            print("\n[Step 5] Database Integration...")
            # Mock the marks logic
            marks = 0
            if final_score >= 90: marks = 5
            elif final_score >= 75: marks = 4
            elif final_score >= 55: marks = 3
            elif final_score >= 35: marks = 2
            elif final_score >= 10: marks = 1
            
            print(f"Marks calculated: {marks}")
            # We won't actually commit to avoid polluting DB, but we check if it reaches here.
            print("\nSuccess: No crash detected in core logic!")

        except Exception:
            print("\n!!! ERROR DETECTED !!!")
            traceback.print_exc()

if __name__ == "__main__":
    reproduce_500()
