import sys
import os
import json

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.services.coding_service import run_test_cases, AIChallenge

def verify():
    app = create_app()
    with app.app_context():
        # 1. Create a challenge with a specific expected function name
        challenge = AIChallenge(
            title="Calculator",
            difficulty="easy",
            description="Add two numbers.",
            language="python",
            test_cases=[
                {"a": 1, "b": 2, "expected": 3}
            ],
            test_wrapper="result = add_numbers({a}, {b})"
        )
        db.session.add(challenge)
        db.session.commit()
        
        problem_id = challenge.id
        
        # Scenario A: User uses a DIFFERENT name
        print("\n--- Test A: Different Function Name ---")
        code_different_name = "def solve_it(a, b):\n    return a + b"
        results, score = run_test_cases(code_different_name, problem_id, 'python')
        print(f"Score: {score}%")
        print(f"Actual: {results[0]['actual']}")
        print(f"Error: {results[0]['error']}")

        # Scenario B: User uses a CLASS
        print("\n--- Test B: Class Method Discovery ---")
        code_class = "class Solution:\n    def add(self, a, b):\n        return a + b"
        results, score = run_test_cases(code_class, problem_id, 'python')
        print(f"Score: {score}%")
        print(f"Actual: {results[0]['actual']}")
        
        # Scenario C: Error in user code (Runtime Error)
        print("\n--- Test C: Runtime Error in User Code ---")
        code_error = "def add_numbers(a, b):\n    return a / 0"
        results, score = run_test_cases(code_error, problem_id, 'python')
        print(f"Error captured: {results[0]['error']}")

        # Clean up
        db.session.delete(challenge)
        db.session.commit()

if __name__ == "__main__":
    verify()
