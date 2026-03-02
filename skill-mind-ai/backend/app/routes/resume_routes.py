import os
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from ..services.resume_service import extract_text_from_file, analyze_resume
from ..models.models import Resume, Skill, db

resume_bp = Blueprint('resume', __name__)

UPLOAD_FOLDER = 'uploads'
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

@resume_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_resume():
    if 'file' not in request.files:
        return jsonify({"message": "No file part"}), 400
    
    file = request.files['file']
    label = request.form.get('label', 'resume1') 
    
    if file.filename == '':
        return jsonify({"message": "No selected file"}), 400
    
    if file:
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        text = extract_text_from_file(file_path)
        analysis = analyze_resume(text)
        
        user_id = int(get_jwt_identity())
        
        resume = Resume.query.filter_by(user_id=user_id, label=label).first()
        if resume:
            resume.filename = filename
            resume.extracted_text = text
            Skill.query.filter_by(resume_id=resume.id).delete()
        else:
            resume = Resume(user_id=user_id, filename=filename, label=label, extracted_text=text)
            db.session.add(resume)
        
        db.session.flush()
        
        for skill in analysis['skills']:
            new_skill = Skill(resume_id=resume.id, skill_name=skill)
            db.session.add(new_skill)
        
        db.session.commit()
        
        return jsonify({
            "message": f"Resume ({label}) analyzed successfully",
            "skills": analysis['skills'],
            "resume_id": resume.id
        }), 200

@resume_bp.route('/compare', methods=['POST'])
@jwt_required()
def compare_resumes():
    data = request.get_json()
    jd_text = data.get('jd', '')
    if not jd_text:
        return jsonify({"message": "No job description provided"}), 400
        
    user_id = int(get_jwt_identity())
    resumes = Resume.query.filter_by(user_id=user_id).all()
    
    if not resumes:
        return jsonify({"message": "No resumes found to compare"}), 400
        
    report = []
    from ..services.resume_service import compare_skills
    
    for r in resumes:
        skills = [s.skill_name for s in Skill.query.filter_by(resume_id=r.id).all()]
        try:
            comparison = compare_skills(skills, jd_text, resume_text=r.extracted_text)
        except Exception as e:
            print(f"Comparison error for {r.label}: {e}")
            comparison = {"score": 0, "matches": [], "missing": [], "insights": "Error during comparison."}
            
        report.append({
            "label": r.label,
            "filename": r.filename,
            "match_score": comparison['score'],
            "matching_skills": comparison['matches'],
            "missing_skills": comparison['missing'],
            "insights": comparison.get('insights', "")
        })
        
    return jsonify({"comparison": report}), 200

@resume_bp.route('/list', methods=['GET'])
@jwt_required()
def list_resumes():
    user_id = int(get_jwt_identity())
    resumes = Resume.query.filter_by(user_id=user_id).all()
    return jsonify({
        "resumes": [
            {
                "id": r.id,
                "label": r.label,
                "filename": r.filename,
                "uploaded_at": r.uploaded_at.isoformat()
            } for r in resumes
        ]
    }), 200
