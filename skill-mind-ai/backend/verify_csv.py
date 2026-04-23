import sys
import os
import json

# Add backend to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app import create_app, db
from app.services.coding_service import run_test_cases, AIChallenge

def verify():
    app = create_app()
    with app.app_context():
        # 1. Create a CSV challenge
        challenge = AIChallenge(
            title="CSV Parser",
            difficulty="medium",
            description="Parse a CSV string into a list of dicts.",
            language="python",
            test_cases=[
                {
                    "input": "Name,RollNo,Dept,Date,Present\nAlice,101,CS,2026-04-20,Y\nBob,102,CS,2026-04-20,N",
                    "expected": [
                        {"name": "Alice", "roll_no": "101", "department": "CS", "date": "2026-04-20", "present": "Y"},
                        {"name": "Bob", "roll_no": "102", "department": "CS", "date": "2026-04-20", "present": "N"}
                    ]
                }
            ],
            test_wrapper="result = parse_attendance({input})"
        )
        db.session.add(challenge)
        db.session.commit()
        
        problem_id = challenge.id
        
        # User's "correct" code from the log
        user_code = """
import csv
import io

def parse_attendance(csv_string):
    f = io.StringIO(csv_string.strip())
    reader = csv.DictReader(f)
    records = []
    for row in reader:
        record = {
            'name': row.get('Name', '').strip(),
            'roll_no': row.get('RollNo', '').strip(),
            'department': row.get('Dept', '').strip(),
            'date': row.get('Date', '').strip(),
            'present': row.get('Present', '').strip()
        }
        records.append(record)
    return records
"""
        
        print("\n--- Testing CSV Parser ---")
        results, score = run_test_cases(user_code, problem_id, 'python')
        print(f"Score: {score}%")
        for res in results:
            print(f"Passed: {res['passed']}")
            print(f"Actual: {res['actual']}")
            print(f"Error: {res['error']}")

        # Clean up
        db.session.delete(challenge)
        db.session.commit()

if __name__ == "__main__":
    verify()
