import os
from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from werkzeug.utils import secure_filename
from ..services.resume_service import extract_text_from_file, analyze_resume
from ..models.models import Resume, Skill, db

resume_bp = Blueprint('resume', __name__)

# Define Upload Folder
UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), '..', '..', 'uploads')
if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

ALLOWED_EXTENSIONS = {'pdf', 'docx', 'txt'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@resume_bp.route('/upload', methods=['POST'])
@jwt_required()
def upload_resume():
    if 'file' not in request.files:
        return jsonify({"message": "No file part"}), 400
    
    file = request.files['file']
    label = request.form.get('label', 'resume1') 
    
    if file.filename == '':
        return jsonify({"message": "No selected file"}), 400
    
    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        file_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(file_path)
        
        # 1. Extraction & AI Analysis
        text = extract_text_from_file(file_path)
        analysis = analyze_resume(text)
        
        user_id = int(get_jwt_identity())
        
        # 2. Database Persistence
        resume = Resume.query.filter_by(user_id=user_id, label=label).first()
        if resume:
            resume.filename = filename
            resume.extracted_text = text
            # Update new structured fields
            resume.structured_data = analysis.get('structured_data')
            resume.resume_score = analysis.get('resume_score', 0.0)
            resume.score_breakdown = analysis.get('score_breakdown')
            resume.skill_confidence = analysis.get('explainability')
            
            # Reset skill mapping
            Skill.query.filter_by(resume_id=resume.id).delete()
        else:
            resume = Resume(
                user_id=user_id, 
                filename=filename, 
                label=label, 
                extracted_text=text,
                structured_data=analysis.get('structured_data'),
                resume_score=analysis.get('resume_score', 0.0),
                score_breakdown=analysis.get('score_breakdown'),
                skill_confidence=analysis.get('explainability')
            )
            db.session.add(resume)
        
        db.session.flush()
        
        # Mapping skills for secondary lookup
        skills_list = analysis.get('skills', [])
        for skill in skills_list:
            new_skill = Skill(resume_id=resume.id, skill_name=skill)
            db.session.add(new_skill)
        
        db.session.commit()
        
        return jsonify({
            "message": f"Resume ({label}) analyzed successfully",
            "score": analysis.get('resume_score'),
            "breakdown": analysis.get('score_breakdown'),
            "structured": analysis.get('structured_data'),
            "skills": skills_list,
            "resume_id": resume.id
        }), 200
    else:
        return jsonify({"message": "Unsupported file format. Use PDF, DOCX, or TXT."}), 400

@resume_bp.route('/job-fit', methods=['POST'])
@jwt_required()
def job_fit():
    """Role-specific job fitting endpoint."""
    data = request.get_json()
    jd_text = data.get('jd', '')
    role_title = data.get('role', 'Unspecified Role')
    
    if not jd_text:
        return jsonify({"message": "No job description provided"}), 400
        
    user_id = int(get_jwt_identity())
    latest_resume = Resume.query.filter_by(user_id=user_id).order_by(Resume.uploaded_at.desc()).first()
    
    if not latest_resume:
        return jsonify({"message": "No resume found. Please upload one first."}), 404
        
    from ..services.resume_service import compare_skills
    skills = [s.skill_name for s in Skill.query.filter_by(resume_id=latest_resume.id).all()]
    
    # role-specific matching
    fit_report = compare_skills(skills, jd_text, resume_text=latest_resume.extracted_text, role_title=role_title)
    
    return jsonify({
        "role": role_title,
        "match_score": fit_report['match_score'],
        "matching_skills": fit_report['matching_skills'],
        "missing_skills": fit_report['missing_skills'],
        "insights": fit_report.get('insights', "")
    }), 200

@resume_bp.route('/compare', methods=['POST'])
@jwt_required()
def compare_resumes():
    # Keep legacy compare for multi-resume overview
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
            comparison = {"match_score": 0, "matching_skills": [], "missing_skills": [], "insights": f"Error during comparison: {str(e)}"}
            
        report.append({
            "label": r.label,
            "filename": r.filename,
            "match_score": comparison['match_score'],
            "matching_skills": comparison['matching_skills'],
            "missing_skills": comparison['missing_skills'],
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
                "score": r.resume_score,
                "uploaded_at": r.uploaded_at.isoformat()
            } for r in resumes
        ]
    }), 200
