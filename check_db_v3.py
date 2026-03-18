import sqlite3
import os

paths = [
    'skill-mind-ai/backend/instance/skill_mind.db',
    'skill-mind-ai/backend/skill_mind.db'
]

for db_path in paths:
    abs_path = os.path.abspath(db_path)
    if os.path.exists(abs_path):
        print(f"\n--- Checking {abs_path} ---")
        try:
            conn = sqlite3.connect(abs_path)
            cursor = conn.cursor()
            cursor.execute("SELECT id, filename, uploaded_at, length(raw_text) FROM resumes ORDER BY uploaded_at DESC LIMIT 3")
            rows = cursor.fetchall()
            print("ID | Filename | Uploaded At | Raw Text Len")
            for r in rows:
                print(f"{r[0]} | {r[1]} | {r[2]} | {r[3]}")
            conn.close()
        except Exception as e:
            print(f"Error: {e}")
    else:
        print(f"\n--- File not found: {abs_path} ---")
