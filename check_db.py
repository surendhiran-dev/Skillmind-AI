
import os
import sys

# Define base path
BACKEND_PATH = os.path.abspath(os.path.join(os.getcwd(), 'skill-mind-ai', 'backend'))
sys.path.append(BACKEND_PATH)

from app import create_app, db
from app.models.models import Resume, Skill

app = create_app()
with app.app_context():
    resumes = Resume.query.all()
    print(f"Total Resumes: {len(resumes)}")
    for r in resumes:
        skills = Skill.query.filter_by(resume_id=r.id).all()
        print(f"ID: {r.id}")
        print(f"  Filename: {r.filename}")
        print(f"  Text Len: {len(r.extracted_text) if r.extracted_text else 0}")
        print(f"  Skills: {[s.skill_name for s in skills]}")
        print("-" * 20)
