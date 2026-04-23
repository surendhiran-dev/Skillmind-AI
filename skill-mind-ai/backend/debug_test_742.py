import sys
import os
import sqlite3
import json

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.services.coding_service import run_test_cases

def run_debug_test(test_id):
    app = create_app()
    with app.app_context():
        db_path = 'instance/skill_mind.db'
        conn = sqlite3.connect(db_path)
        cursor = conn.cursor()
        
        # Get the submission
        cursor.execute("SELECT problem_statement, submitted_code, language FROM coding_tests WHERE id = ?", (test_id,))
        row = cursor.fetchone()
        if not row:
            print("Test not found!")
            return
            
        prob_stmt, code, lang = row
        print(f"Running Test ID: {test_id}")
        # print(f"Code:\n{code}")
        
        # Since problem_statement is the title, let's find the AI challenge by title
        cursor.execute("SELECT id, test_cases, test_wrapper FROM ai_challenges WHERE title = ? ORDER BY created_at DESC LIMIT 1", (prob_stmt,))
        prob = cursor.fetchone()
        if not prob:
            print("Problem details not found in ai_challenges!")
            return
            
        prob_id, tc_json, wrapper = prob
        print(f"Using Problem ID: {prob_id}")
        # print(f"Wrapper: {wrapper}")
        
        results, score = run_test_cases(code, prob_id, lang)
        print(f"Score: {score}%")
        for res in results:
            print(f"Test {res['test']}: {'PASS' if res['passed'] else 'FAIL'}")
            print(f"  Input: {str(res['input'])[:50]}...")
            print(f"  Expected: {str(res['expected'])[:100]}...")
            print(f"  Actual: {res['actual']}")
            print(f"  Error: {res['error']}")
            
        conn.close()

if __name__ == "__main__":
    run_debug_test(742)
