import sys
import os

# Mock the database and other dependencies to test the backend logic standalone
sys.path.append('D:/finalcode/skill-mind-ai/backend')

from app.services.coding_service import evaluate_code_quality, _run_single_test, _is_equivalent

def test_quality():
    print("--- Testing Quality Score ---")
    
    # Correct code with function and docstring but NO class
    code_good = """
def get_teacher_attendance(records):
    \"\"\"Calculates attendance percentage.\"\"\"
    attendance_map = {}
    for name, status in records:
        if name not in attendance_map:
            attendance_map[name] = [0, 0]
        attendance_map[name][1] += 1
        if status == 'present':
            attendance_map[name][0] += 1
            
    results = {}
    for name, counts in attendance_map.items():
        results[name] = round((counts[0] / counts[1]) * 100, 2)
    return results
"""
    res = evaluate_code_quality(code_good)
    print(f"Good Code Score: {res['score']}/100")
    print(f"Feedback: {res['feedback']}")
    assert res['score'] == 100, "Score should be 100 for this correct implementation"

def test_fallback_wrapper():
    print("\n--- Testing Wrapper Fallback ---")
    
    # Problem originally set up for Java
    problem = {
        "title": "Teacher Attendance",
        "test_wrapper": "result = AttendanceCalculator.calculateAttendance({records})",
        "test_cases": [{"input": {"records": [["Alice", "present"]]}, "expected": {"Alice": 100.0}}]
    }
    
    # User provides Python code with a different function name
    code = """
def my_custom_attendance_func(records):
    return {"Alice": 100.0}
"""
    
    # This would have failed before due to NameError 'AttendanceCalculator'
    # Now it should use _get_func_name('my_custom_attendance_func') as fallback
    res = _run_single_test(code, problem, problem["test_cases"][0], 1, language='python')
    print(f"Test Result Passed: {res['passed']}")
    if not res['passed']:
        print(f"Error: {res.get('error')}")
        print(f"Actual: {res.get('actual')}")
    
    assert res['passed'] == True, "Fallback should have correctly identified and called the function"

def test_missing_input_key():
    print("\n--- Testing Missing Input Key Resilience ---")
    
    # Test case uses "records" instead of "input"
    problem = {
        "title": "LFU Cache Simulator",
        "test_wrapper": "result = process_ops({records})",
        "test_cases": [{"records": [1, 2, 3], "expected": [1, 2, 3]}]
    }
    
    code = "def process_ops(records): return records"
    
    # This would have caused KeyError: 'input' before
    try:
        res = _run_single_test(code, problem, problem["test_cases"][0], 1, language='python')
        print(f"Test Result Passed: {res['passed']}")
        assert res['passed'] == True
    except KeyError as e:
        print(f"Error: KeyError encountered: {e}")
        assert False, "Should not raise KeyError"

def test_equivalence():
    print("\n--- Testing Equivalence Logic ---")
    assert _is_equivalent(100, 100.0) == True
    assert _is_equivalent(99.99, 100.0) == False
    assert _is_equivalent("100", 100) == True
    assert _is_equivalent({"A": 1}, {"A": 1.0}) == True
    print("Equivalence tests passed")

if __name__ == "__main__":
    try:
        test_quality()
        test_fallback_wrapper()
        test_missing_input_key()
        test_equivalence()
        print("\nALL SCORING FIX TESTS PASSED!")
    except Exception as e:
        print(f"\nTEST FAILED: {e}")
        sys.exit(1)
