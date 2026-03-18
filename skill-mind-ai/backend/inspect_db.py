import sqlite3
import os

db_path = 'instance/skill_mind.db'
if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    try:
        cursor.execute("SELECT * FROM users;")
        rows = cursor.fetchall()
        print("Users table:")
        for row in rows:
            print(row)
            
        cursor.execute("SELECT * FROM interview_sessions;")
        rows = cursor.fetchall()
        print("\nInterview Sessions table:")
        for row in rows:
            print(row)
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()
else:
    print(f"DB not found at {db_path}")
