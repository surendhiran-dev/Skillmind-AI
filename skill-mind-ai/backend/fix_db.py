
import sqlite3
import os

db_paths = [
    os.path.join(os.path.dirname(__file__), 'skill_mind.db'),
    os.path.join(os.path.dirname(__file__), 'instance', 'skill_mind.db')
]

for db_path in db_paths:
    if not os.path.exists(db_path):
        print(f"Skipping non-existent DB: {db_path}")
        continue
        
    print(f"\nChecking database at: {db_path}")
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Check if 'users' table exists
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='users'")
    if not cursor.fetchone():
        print(f"Table 'users' not found in {db_path}. Skipping.")
        conn.close()
        continue

    # Get existing columns
    cursor.execute("PRAGMA table_info(users)")
    columns = [row[1] for row in cursor.fetchall()]
    print(f"Current columns in 'users' table: {columns}")

    new_columns = {
        "full_name": "TEXT",
        "profile_photo": "TEXT",
        "bio": "TEXT",
        "phone": "TEXT"
    }

    added = False
    for col, type_ in new_columns.items():
        if col not in columns:
            print(f"Adding column '{col}' to 'users' table...")
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col} {type_}")
            added = True

    if added:
        conn.commit()
        print("Database updated successfully.")
    else:
        print("All columns already exist.")

    conn.close()
