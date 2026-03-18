
import os
import sys

BACKEND_PATH = os.path.abspath(os.path.join(os.getcwd(), 'skill-mind-ai', 'backend'))
sys.path.append(BACKEND_PATH)

from app import create_app, db
from app.models.models import Resume

from app.services.ai_service import local_extract_skills

app = create_app()
with app.app_context():
    r = Resume.query.get(1)
    if r:
        print(f"ID: {r.id}, Filename: {r.filename}")
        print("-" * 50)
        skills = local_extract_skills(r.extracted_text)
        print(f"Extracted Skills: {skills}")
        print("-" * 50)
    else:
        print("Resume ID 1 not found")
