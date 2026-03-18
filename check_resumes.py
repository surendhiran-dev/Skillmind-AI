import sqlite3
import os

db_path = os.path.join('skill-mind-ai', 'backend', 'instance', 'skill_mind.db')
if not os.path.exists(db_path):
    print(f"Database not found at {db_path}")
    # Try alternate path
    db_path = os.path.join('skill-mind-ai', 'backend', 'skill_mind.db')

if os.path.exists(db_path):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("SELECT id, filename, uploaded_at, length(raw_text) FROM resumes ORDER BY uploaded_at DESC LIMIT 5")
    rows = cursor.fetchall()
    print("RESUMES TABLE (Latest 5):")
    print("ID | Filename | Uploaded At | Raw Text Length")
    for r in rows:
        print(f"{r[0]} | {r[1]} | {r[2]} | {r[3]}")
    conn.close()
else:
    print("Database not found.")
