from app import create_app, db
from app.models.models import User, Score, Resume, Skill
from datetime import datetime

def seed_data():
    app = create_app()
    with app.app_context():
        user = User.query.filter_by(username='admin').first()
        if not user:
            print("User admin not found")
            return
            
        # Create a dummy resume
        resume = Resume(
            user_id=user.id,
            filename='resume.pdf',
            label='resume1',
            extracted_text='Python Backend Developer with 5 years experience in Flask and SQL.',
            uploaded_at=datetime.utcnow()
        )
        db.session.add(resume)
        db.session.flush()
        
        # Add skills
        skills = [
            Skill(resume_id=resume.id, skill_name='Python', category='Language'),
            Skill(resume_id=resume.id, skill_name='Flask', category='Framework'),
            Skill(resume_id=resume.id, skill_name='SQL', category='Database')
        ]
        for s in skills: db.session.add(s)
        
        # Create a Score report
        report = Score(
            user_id=user.id,
            resume_strength=85,
            quiz_score=75,
            coding_score=80,
            skill_gaps=[
                {'category': 'Python', 'status': 'Strong', 'suggestion': 'Excellent'},
                {'category': 'Flask', 'status': 'Moderate', 'suggestion': 'Learn more about Blueprints'},
                {'category': 'Docker', 'status': 'Weak', 'suggestion': 'Essential for deployment'}
            ],
            generated_at=datetime.utcnow()
        )
        db.session.add(report)
        db.session.commit()
        print("Seeded assessment data for user 'admin'")

if __name__ == "__main__":
    seed_data()
