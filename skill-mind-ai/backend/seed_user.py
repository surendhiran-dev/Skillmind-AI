from app import create_app, db
from app.models.models import User

def seed_user():
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(username='admin').first()
        if not user:
            print("Creating default user...")
            user = User(
                username='admin',
                email='admin@example.com',
                role='admin'
            )
            user.set_password('admin123')
            db.session.add(user)
            db.session.commit()
            print("Default user created: admin / admin123")
        else:
            print("User 'admin' already exists. Updating password to 'admin123'...")
            user.set_password('admin123')
            db.session.commit()
            print("Password updated for 'admin'.")

if __name__ == "__main__":
    seed_user()
