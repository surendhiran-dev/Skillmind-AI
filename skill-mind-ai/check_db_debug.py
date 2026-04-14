import sys
import os
sys.path.append(os.path.join(os.getcwd(), 'backend'))
from backend.app import create_app
from backend.app.models.models import User

app = create_app()
with app.app_context():
    users = User.query.all()
    for u in users:
        print(f"ID: {u.id}, Username: {u.username}, Full Name: {u.full_name}, Bio: {u.bio}")
