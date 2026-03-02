import sqlite3
import os

db_path = 'd:/finalcode/skill-mind-ai/backend/instance/skill_mind.db'
if not os.path.exists(db_path):
    # Try alternate location if instance folder is different
    db_path = 'd:/finalcode/skill-mind-ai/backend/skill_mind.db'

print(f"Connecting to database at: {db_path}")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # Check existing columns
    cursor.execute("PRAGMA table_info(resumes)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"Current columns in 'resumes': {columns}")
    
    new_columns = [
        ("structured_data", "JSON"),
        ("resume_score", "FLOAT DEFAULT 0.0"),
        ("score_breakdown", "JSON"),
        ("skill_confidence", "JSON")
    ]
    
    for col_name, col_type in new_columns:
        if col_name not in columns:
            print(f"Adding column: {col_name}")
            cursor.execute(f"ALTER TABLE resumes ADD COLUMN {col_name} {col_type}")
        else:
            print(f"Column {col_name} already exists.")
            
    conn.commit()
    conn.close()
    print("Database migration successful!")
except Exception as e:
    print(f"Migration failed: {e}")
