from app import create_app, db
from sqlalchemy import text

app = create_app()
with app.app_context():
    try:
        db.session.execute(text("ALTER TABLE quizzes ADD COLUMN duration INTEGER"))
        print("Added quizzes.duration")
    except Exception as e:
        print(f"Skipping quizzes.duration: {e}")

    try:
        db.session.execute(text("ALTER TABLE coding_tests ADD COLUMN duration INTEGER"))
        print("Added coding_tests.duration")
    except Exception as e:
        print(f"Skipping coding_tests.duration: {e}")

    try:
        db.session.execute(text("ALTER TABLE coding_tests ADD COLUMN completed_at DATETIME"))
        print("Added coding_tests.completed_at")
    except Exception as e:
        print(f"Skipping coding_tests.completed_at: {e}")

    try:
        db.session.execute(text("ALTER TABLE hr_sessions ADD COLUMN duration INTEGER"))
        print("Added hr_sessions.duration")
    except Exception as e:
        print(f"Skipping hr_sessions.duration: {e}")

    try:
        db.session.execute(text("ALTER TABLE hr_sessions ADD COLUMN completed_at DATETIME"))
        print("Added hr_sessions.completed_at")
    except Exception as e:
        print(f"Skipping hr_sessions.completed_at: {e}")

    db.session.commit()
    print("Migration complete")
