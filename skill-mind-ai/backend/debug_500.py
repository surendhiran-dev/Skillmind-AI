import os
from app import create_app
from app.models.models import Score, Resume, Skill, User, db

app = create_app()

def debug_stats():
    with app.app_context():
        print("--- Debugging /api/dashboard/stats ---")
        # Find a test user
        user = User.query.first()
        if not user:
            print("No users found.")
            return
        
        user_id = user.id
        print(f"Testing for user_id: {user_id}")
        
        try:
            report = Score.query.filter_by(user_id=user_id).order_by(Score.generated_at.desc()).first()
            print(f"Report found: {report}")
            if report:
                print(f"Report scores: quiz={report.quiz_score}, coding={report.coding_score}, interview={report.interview_score}, resume={report.resume_strength}")
            
            latest_resume = Resume.query.filter_by(user_id=user_id).order_by(Resume.uploaded_at.desc()).first()
            print(f"Latest resume: {latest_resume}")
            
            skills = []
            if latest_resume:
                skills = [s.skill_name for s in Skill.query.filter_by(resume_id=latest_resume.id).all()]
            print(f"Skills: {skills}")
            
            from app.services.ai_service import generate_job_recommendations_llm
            print("Calling generate_job_recommendations_llm...")
            recommendations = generate_job_recommendations_llm(skills, report.final_score if report else 0)
            print(f"Recommendations: {recommendations}")
            
            print("Constructing response...")
            res = {
                "report": {
                    "final_score": report.final_score if report else 0,
                    "quiz_score": report.quiz_score if report else 0,
                    "coding_score": report.coding_score if report else 0,
                    "interview_score": report.interview_score if report else 0,
                    "resume_strength": report.resume_strength if report else 0,
                    "marks": {
                        "resume": round((report.resume_strength / 100) * 10, 1) if report and report.resume_strength is not None else 0,
                        "quiz": round((report.quiz_score / 100) * 30, 1) if report and report.quiz_score is not None else 0,
                        "coding": round((report.coding_score / 100) * 30, 1) if report and report.coding_score is not None else 0,
                        "interview": round((report.interview_score / 100) * 30, 1) if report and report.interview_score is not None else 0,
                        "total": round(report.final_score, 1) if report and report.final_score is not None else 0
                    },
                } if report else None
            }
            print(f"Constructed res: {res}")
            print("SUCCESS: /api/dashboard/stats logic works.")
            
        except Exception as e:
            print(f"ERROR: {e}")
            import traceback
            traceback.print_exc()

if __name__ == "__main__":
    debug_stats()
