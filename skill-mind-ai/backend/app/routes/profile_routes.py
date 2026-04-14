from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models.models import User, Quiz, CodingTest, db, Resume, InterviewReport, InterviewSession

profile_bp = Blueprint('profile', __name__)

@profile_bp.route('/', methods=['GET'])
@jwt_required()
def get_profile():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404
    
    # Get history
    quizzes = Quiz.query.filter_by(user_id=user_id).order_by(Quiz.completed_at.desc()).all()
    coding_tests = CodingTest.query.filter_by(user_id=user_id).order_by(CodingTest.completed_at.desc()).all()
    resumes = Resume.query.filter_by(user_id=user_id).order_by(Resume.uploaded_at.desc()).all()
    interviews = InterviewReport.query.join(InterviewSession).filter(InterviewSession.user_id == user_id).order_by(InterviewReport.generated_at.desc()).all()
    
    return jsonify({
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "bio": user.bio,
            "phone": user.phone,
            "profile_photo": user.profile_photo,
            "role": user.role
        },
        "history": {
            "quizzes": [
                {
                    "id": q.id, 
                    "score": q.score, 
                    "skill": q.skill_category, 
                    "date": q.completed_at.isoformat() if q.completed_at else None
                } for q in quizzes
            ],
            "coding": [
                {
                    "id": c.id, 
                    "score": c.score, 
                    "problem": (c.problem_statement[:50] + "...") if c.problem_statement else "Unknown Problem", 
                    "date": c.completed_at.isoformat() if c.completed_at else None
                } for c in coding_tests
            ],
            "resume": [
                {
                    "id": r.id,
                    "score": r.resume_score,
                    "filename": r.filename,
                    "date": r.uploaded_at.isoformat() if r.uploaded_at else None
                } for r in resumes
            ],
            "interview": [
                {
                    "id": i.id,
                    "score": i.hr_interview_score,
                    "date": i.generated_at.isoformat() if i.generated_at else None
                } for i in interviews
            ]
        }
    }), 200

@profile_bp.route('/', methods=['PUT'])
@jwt_required()
def update_profile():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404
    
    data = request.get_json()
    if not data:
        return jsonify({"message": "No data provided"}), 400
    
    if 'full_name' in data:
        user.full_name = data['full_name']
    if 'bio' in data:
        user.bio = data['bio']
    if 'phone' in data:
        user.phone = data['phone']
    if 'profile_photo' in data:
        user.profile_photo = data['profile_photo']
        
    db.session.commit()
    
    return jsonify({"message": "Profile updated successfully"}), 200
