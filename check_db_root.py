import sqlite3
import os

db_path = os.path.join('skill-mind-ai', 'backend', 'skill_mind.db')
output_path = 'db_check_root.txt'
if not os.path.exists(db_path):
    with open(output_path, 'w') as f:
        f.write(f"Database not found at {db_path}")
else:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute("PRAGMA table_info(resumes)")
    columns = cursor.fetchall()
    with open(output_path, 'w') as f:
        f.write("Columns in 'resumes' table:\n")
        for col in columns:
            f.write(str(col) + "\n")
    conn.close()
    print(f"Results written to {output_path}")
