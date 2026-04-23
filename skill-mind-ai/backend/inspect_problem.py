import sqlite3
import json
import os

def dump_details(test_id):
    db_path = 'instance/skill_mind.db'
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Get problem_id from coding_tests
    cursor.execute("SELECT problem_statement, submitted_code FROM coding_tests WHERE id = ?", (test_id,))
    row = cursor.fetchone()
    if not row:
        print("Test not found!")
        return
        
    prob_stmt, code = row
    print(f"Problem ID/Statement: {prob_stmt}")
    
    # Try to find problem details
    try:
        prob_id = int(prob_stmt)
        cursor.execute("SELECT title, language, test_cases, test_wrapper FROM ai_challenges WHERE id = ?", (prob_id,))
        prob = cursor.fetchone()
        if prob:
            print(f"Title: {prob[0]}")
            print(f"Language: {prob[1]}")
            print(f"Test Wrapper: {prob[3]}")
            print(f"Test Cases: {prob[2]}")
    except:
        print(f"Problem statement is text: {prob_stmt[:100]}")
    
    conn.close()

if __name__ == "__main__":
    dump_details(742)
