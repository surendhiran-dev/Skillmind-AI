import sqlite3
import json
import os

db_path = 'D:/finalcode/skill-mind-ai/backend/instance/skill_mind.db'

def view_problem():
    if not os.path.exists(db_path):
        print(f"DB not found at {db_path}")
        return

    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    cursor.execute('''
        SELECT id, title, test_cases, test_wrapper 
        FROM ai_challenges 
        WHERE title LIKE "LFU %"
        ORDER BY id DESC LIMIT 1
    ''')
    
    r = cursor.fetchone()
    if r:
        print(f"ID: {r[0]}")
        print(f"Title: {r[1]}")
        print(f"Test cases Type: {type(r[2])}")
        print(f"Test cases Content: {r[2]}")
        try:
            tc = json.loads(r[2])
            print(f"Parsed Test cases: {json.dumps(tc, indent=2)}")
        except Exception as e:
            print(f"Failed to parse JSON: {e}")
            # Maybe it's already a dict/list if using some library, but sqlite returns string
    else:
        print("LFU Problem not found")

    conn.close()

if __name__ == "__main__":
    view_problem()
