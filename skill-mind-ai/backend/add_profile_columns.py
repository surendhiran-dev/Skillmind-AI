import sqlite3
import os

db_path = os.path.join(os.path.dirname(__file__), 'skill_mind.db')
print(f"Connecting to database at {db_path}...")

try:
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()

    # Add columns if they don't exist
    columns_to_add = [
        ('full_name', 'VARCHAR(100)'),
        ('profile_photo', 'TEXT'),
        ('bio', 'TEXT'),
        ('phone', 'VARCHAR(20)')
    ]

    for col_name, col_type in columns_to_add:
        try:
            cursor.execute(f"ALTER TABLE users ADD COLUMN {col_name} {col_type}")
            print(f"Added column {col_name}")
        except sqlite3.OperationalError as e:
            if "duplicate column name" in str(e).lower():
                print(f"Column {col_name} already exists.")
            else:
                print(f"Error adding column {col_name}: {e}")

    conn.commit()
    conn.close()
    print("Migration completed successfully.")

except Exception as e:
    print(f"An error occurred: {e}")
