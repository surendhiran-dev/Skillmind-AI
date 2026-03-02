from app import create_app, db
from app.models.models import User, Resume, ExtractedSkill

app = create_app()
with app.app_context():
    user = User.query.filter_by(username='admin').first()
    if not user:
        print("Admin user not found.")
    else:
        print(f"User: {user.username} (ID: {user.id})")
        resumes = Resume.query.filter_by(user_id=user.id).all()
        print(f"Number of resumes: {len(resumes)}")
        for r in resumes:
            skills = ExtractedSkill.query.filter_by(resume_id=r.id).all()
            print(f"  Resume ID: {r.id}, Label: {r.label}, Skills Count: {len(skills)}")
            for s in skills:
                print(f"    - {s.skill_name}")
