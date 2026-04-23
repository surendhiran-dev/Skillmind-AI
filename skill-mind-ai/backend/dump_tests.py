import sqlite3
import json
import os

def dump_tests():
    # Try multiple paths
    paths = ['instance/skill_mind.db', 'skill_mind.db', '../instance/skill_mind.db']
    db_path = None
    for p in paths:
        if os.path.exists(p):
            db_path = p
            break
            
    if not db_path:
        print("Database not found!")
        return

    print(f"Using database: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, problem_statement, submitted_code, quality_report FROM coding_tests ORDER BY completed_at DESC LIMIT 5;")
    rows = cursor.fetchall()
    for row in rows:
        print(f"ID: {row[0]}")
        print(f"Problem: {row[1][:100]}...")
        print(f"Code:\n{row[2]}")
        # print(f"Report: {row[3]}")
        print("-" * 40)
    conn.close()

if __name__ == "__main__":
    dump_tests()
