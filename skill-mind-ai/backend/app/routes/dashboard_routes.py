from flask import Blueprint, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models.models import Score, Quiz, CodingTest, Resume, Skill, User, InterviewSession, db

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/stats', methods=['GET'])
@jwt_required()
def get_stats():
    raw_identity = get_jwt_identity()
    try:
        # Try to convert to int if it's a numeric string or 'user_123'
        if isinstance(raw_identity, str) and raw_identity.startswith('user_'):
            user_id = int(raw_identity.replace('user_', ''))
        else:
            user_id = int(raw_identity)
    except (ValueError, TypeError):
        # Fallback to string identity if not numeric (e.g. Clerk UUID)
        # We'd need to find the user by this identity string
        user = User.query.filter((User.id == raw_identity) | (User.username == raw_identity)).first()
        if not user:
             return jsonify({"error": "User identity mapping failed", "identity": raw_identity}), 401
        user_id = user.id

    # Latest report
    report = Score.query.filter_by(user_id=user_id).order_by(Score.generated_at.desc()).first()

    # History
    quizzes = Quiz.query.filter_by(user_id=user_id).order_by(Quiz.id.desc()).limit(10).all()
    coding_tests = CodingTest.query.filter_by(user_id=user_id).order_by(CodingTest.id.desc()).limit(10).all()
    interviews = InterviewSession.query.filter_by(user_id=user_id, status='completed').order_by(InterviewSession.ended_at.desc()).limit(10).all()

    # Skills
    latest_resume = Resume.query.filter_by(user_id=user_id).order_by(Resume.uploaded_at.desc()).first()
    skills = []
    if latest_resume:
        skills = [s.skill_name for s in Skill.query.filter_by(resume_id=latest_resume.id).all()]

    # Job Recommendations
    from ..services.ai_service import generate_job_recommendations_llm
    job_recommendations = generate_job_recommendations_llm(skills, report.final_score if report and hasattr(report, 'final_score') else 0)

    # Check for Interview Cooldown
    from datetime import datetime, timedelta
    cooldown_active = False
    remaining_minutes = 0
    last_terminated = InterviewSession.query.filter(
        InterviewSession.user_id == user_id,
        InterviewSession.termination_reason.like('security%')
    ).order_by(InterviewSession.ended_at.desc()).first()

    if last_terminated and last_terminated.ended_at:
        diff = datetime.utcnow() - last_terminated.ended_at
        if diff < timedelta(minutes=30):
            cooldown_active = True
            remaining_minutes = 30 - int(diff.total_seconds() / 60)

    res = {
        "report": {
            "final_score": report.final_score if report else 0,
            "quiz_score": report.quiz_score if report else 0,
            "coding_score": report.coding_score if report else 0,
            "interview_score": report.interview_score if report else 0,
            "resume_strength": report.resume_strength if report else 0,
            "readiness_level": report.readiness_report if report else "Needs Improvement",
            "marks": {
                "resume": round(((report.resume_strength or 0) / 100) * 10, 1) if report else 0,
                "quiz": round(((report.quiz_score or 0) / 100.0) * 30, 1) if report else 0,
                "coding": round(((report.coding_score or 0) / 100.0) * 30, 1) if report else 0,
                "interview": round(((report.interview_score or 0) / 100.0) * 30, 1) if report else 0,
                "total": round(report.final_score or 0, 1) if report else 0
            },
            "analysis": report.skill_gaps if report and report.skill_gaps else [],
        } if report else None,
        "quiz_history": [{"score": q.score} for q in quizzes],
        "coding_history": [{"score": c.score, "problem": c.problem_statement} for c in coding_tests],
        "interview_history": [{"score": i.report.hr_interview_score if i.report else 0, "date": i.ended_at.strftime('%Y-%m-%d')} for i in interviews],
        "skills": skills,
        "job_recommendations": job_recommendations,
        "cooldown": {
            "active": cooldown_active,
            "remaining_minutes": max(0, remaining_minutes)
        }
    }
    return jsonify(res), 200
