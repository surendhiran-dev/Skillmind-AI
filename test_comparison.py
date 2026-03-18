import sys
import os

# Add the backend app to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), 'skill-mind-ai', 'backend')))

from app import create_app
from app.services.resume_service import compare_skills

app = create_app()
with app.app_context():
    resume_text = "Experienced Senior Python Developer with 5 years in AWS, Docker, and React. Bachelor's Degree in CS."
    jd_text = "We need a Senior Python Developer with AWS and Docker experience. Degree required."
    resume_skills = ["Python", "AWS", "Docker", "React"]
    
    result = compare_skills(resume_skills, jd_text, resume_text, "Senior Developer")
    print("MATCH SCORE:", result.get("match_score"))
    print("INSIGHTS:", result.get("insights"))
    print("BREAKDOWN:", result.get("breakdown"))
    print("METHOD:", result.get("method"))
