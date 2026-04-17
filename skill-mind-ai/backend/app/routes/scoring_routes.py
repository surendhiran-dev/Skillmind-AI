from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models.models import Quiz, CodingTest, HRSession, Score, SkillGapReport, db, Resume
from ..services.scoring_service import refresh_user_score
from datetime import datetime

scoring_bp = Blueprint('scoring', __name__)

def calculate_resume_strength(user_id):
    resume = Resume.query.filter_by(user_id=user_id).order_by(Resume.uploaded_at.desc()).first()
    if not resume:
        return 0
    text_len = len(resume.extracted_text) if resume.extracted_text else 0
    return min((text_len / 1000) * 50 + 50, 100)

@scoring_bp.route('/generate-report', methods=['POST'])
@jwt_required()
def generate_report():
    user_id = int(get_jwt_identity())
    
    try:
        report = refresh_user_score(user_id)
        
        # Return data in the expected format for the frontend
        return jsonify({
            "final_score": report.final_score,
            "quiz_score": report.quiz_score,
            "coding_score": report.coding_score,
            "interview_score": report.interview_score,
            "resume_strength": report.resume_strength,
            "marks": {
                "resume": round((report.resume_strength / 100) * 10, 1),
                "quiz": round((report.quiz_score / 100) * 30, 1),
                "coding": round((report.coding_score / 100) * 30, 1),
                "interview": round((report.interview_score / 100) * 30, 1),
                "total": round(report.final_score, 1)
            },
            "analysis": report.skill_gaps,
            "report_id": report.id
        }), 200
    except Exception as e:
        import traceback
        print(traceback.format_exc())
        return jsonify({"error": "Failed to generate report", "details": str(e)}), 500
