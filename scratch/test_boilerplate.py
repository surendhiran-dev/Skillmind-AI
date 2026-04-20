import sys
import os

# Mock the backend to test the logic
sys.path.append('D:/finalcode/skill-mind-ai/backend')

from app.services.coding_service import evaluate_code_quality

def test_boilerplate():
    print("--- Testing Boilerplate Detection ---")
    
    # This is the "default syntax"
    code_boilerplate = """
def room_allocation_for_teacher_schedules(*args):
    # Write your solution here
    pass
"""
    res = evaluate_code_quality(code_boilerplate)
    print(f"Boilerplate Score: {res['score']}/100")
    print(f"Feedback: {res['feedback']}")
    assert res['score'] == 15, "Boilerplate score should be 15"

def test_real_code():
    print("\n--- Testing Real Implementation ---")
    
    # This has logic
    code_real = """
def solve(n):
    for i in range(n):
        print(i)
    return True
"""
    res = evaluate_code_quality(code_real)
    print(f"Real Code Score: {res['score']}/100")
    assert res['score'] > 60, "Real code should have a normal score"

if __name__ == "__main__":
    try:
        test_boilerplate()
        test_real_code()
        print("\nBOILERPLATE DETECTION TESTS PASSED!")
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        sys.exit(1)
