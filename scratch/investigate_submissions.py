import sqlite3
import json
import os

db_path = 'D:/finalcode/skill-mind-ai/backend/instance/skill_mind.db'

def investigate():
    if not os.path.exists(db_path):
        print(f"DB not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Find the most recent coding test that isn't a summary
    cursor.execute('''
        SELECT id, problem_statement, submitted_code, score, quality_report 
        FROM coding_tests 
        WHERE problem_statement != "Full Assessment Summary"
        ORDER BY id DESC LIMIT 5
    ''')
    
    rows = cursor.fetchall()
    for r in rows:
        print(f"\n{'='*50}")
        print(f"ID: {r[0]}")
        print(f"Problem: {r[1]}")
        print(f"Score: {r[3]}")
        print(f"Quality Report: {r[4]}")
        print(f"Code Sample (first 200 chars):\n{r[2][:200]}...")
        
        # If it's the attendance one, let's look at the full code
        if "Attendance" in r[1]:
            print(f"\nFULL CODE for ID {r[0]}:\n{r[2]}")

    conn.close()

if __name__ == "__main__":
    investigate()
