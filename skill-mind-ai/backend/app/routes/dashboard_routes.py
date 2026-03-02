from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models.models import Score, Quiz, CodingTest, Resume, Skill, db

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_stats():
    user_id = int(get_jwt_identity())

    # Latest report
    report = Score.query.filter_by(user_id=user_id).order_by(Score.generated_at.desc()).first()

    # History
    quizzes = Quiz.query.filter_by(user_id=user_id).order_by(Quiz.id.desc()).limit(10).all()
    coding_tests = CodingTest.query.filter_by(user_id=user_id).order_by(CodingTest.id.desc()).limit(10).all()

    # Skills
    latest_resume = Resume.query.filter_by(user_id=user_id).order_by(Resume.uploaded_at.desc()).first()
    skills = []
    if latest_resume:
        skills = [s.skill_name for s in Skill.query.filter_by(resume_id=latest_resume.id).all()]

    # Job Recommendations
    from ..services.ai_service import generate_job_recommendations_llm
    job_recommendations = generate_job_recommendations_llm(skills, report.final_score if report and hasattr(report, 'final_score') else 0)

    res = {
        "report": {
            "final_score": report.final_score if report else 0,
            "quiz_score": report.quiz_score if report else 0,
            "coding_score": report.coding_score if report else 0,
            "interview_score": report.interview_score if report else 0,
            "resume_strength": report.resume_strength if report else 0,
            "marks": {
                "resume": round((report.resume_strength / 100) * 10, 1) if report else 0,
                "quiz": round((report.quiz_score / 100) * 30, 1) if report else 0,
                "coding": round((report.coding_score / 100) * 30, 1) if report else 0,
                "interview": round((report.interview_score / 100) * 30, 1) if report else 0,
                "total": round(report.final_score, 1) if report else 0
            },
            "analysis": report.skill_gaps if report else [],
        } if report else None,
        "quiz_history": [{"score": q.score} for q in quizzes],
        "coding_history": [{"score": c.score, "problem": c.problem_statement} for c in coding_tests],
        "skills": skills,
        "job_recommendations": job_recommendations
    }
    return jsonify(res), 200
