from app import create_app, db
from app.models.models import User

app = create_app()
with app.app_context():
    users = User.query.all()
    for u in users:
        print(f"ID: {u.id}, Username: {u.username}, Email: {u.email}")
