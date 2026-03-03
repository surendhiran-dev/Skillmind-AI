import random
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..services.quiz_service import generate_questions, evaluate_answer
from ..models.models import Skill, Quiz, db, Resume

quiz_bp = Blueprint('quiz', __name__)

@quiz_bp.route('/generate', methods=['POST', 'GET'])
@jwt_required()
def start_quiz():
    user_id = int(get_jwt_identity())
    data = request.get_json() if request.method == 'POST' else {}
    jd_text = data.get('jd', '')
    
    # Get user's latest resume
    resume = Resume.query.filter_by(user_id=user_id).order_by(Resume.uploaded_at.desc()).first()
        
    if not resume:
        return jsonify({"message": "Please upload a resume first"}), 400
    
    resume_skills = [s.skill_name for s in Skill.query.filter_by(resume_id=resume.id).all()]
    
    # If JD is provided, prioritize skills that overlap or are in JD
    if jd_text:
        from ..services.resume_service import analyze_resume
        jd_analysis = analyze_resume(jd_text)
        jd_skills = jd_analysis['skills']
        
        # Priority: Overlap -> JD Skills -> Resume Skills
        overlap = [s for s in jd_skills if s in resume_skills]
        if overlap:
            skill_names = overlap
        else:
            skill_names = jd_skills if jd_skills else resume_skills
    else:
        skill_names = resume_skills
    
    if not skill_names:
        skill_names = ["Python", "JavaScript", "SQL"] # Fallback
        
    # Limit to 15 diverse skills if many
    if len(skill_names) > 15:
        skill_names = random.sample(skill_names, 15)
        
    questions = generate_questions(skill_names, jd_text)
    return jsonify({"questions": questions}), 200

@quiz_bp.route('/submit', methods=['POST'])
@jwt_required()
def submit_quiz():
    data = request.get_json()
    user_id = int(get_jwt_identity())
    
    total_marks = 0
    responses = data.get('responses', [])
    
    if not responses:
        return jsonify({"message": "No responses provided"}), 400
    
    results = []
    for resp in responses:
        marks = evaluate_answer(resp['question'], resp['answer'])
        total_marks += marks
        results.append({
            "question": resp['question'],
            "marks": marks,
            "max_marks": 2
        })
    
    # Total marks out of 30 (15 questions × 2 marks each)
    max_total = len(responses) * 2  # Should be 30 for 15 questions
    score_pct = (total_marks / max_total * 100) if max_total > 0 else 0
    
    new_quiz = Quiz(user_id=user_id, skill_category="Mixed", score=score_pct)
    db.session.add(new_quiz)
    db.session.commit()
    
    return jsonify({
        "message": "Quiz submitted",
        "score": score_pct,
        "total_marks": total_marks,
        "max_marks": max_total,
        "results": results
    }), 200
