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
        from .. import socketio
        socketio.emit('analysis_progress', {'step': 'extract', 'message': 'Extracting Resume Entities...'}, namespace='/')
        text = extract_text_from_file(file_path)
        
        # Step 7: Normalizing Taxonomy (Part of extraction logic)
        socketio.emit('analysis_progress', {'step': 'normalization', 'message': 'Normalizing Skill Taxonomy...'}, namespace='/')
        
        # The analyze_resume function now handles the subsequent steps internally
        analysis = analyze_resume(text) # Assuming analyze_resume is updated to handle the steps
        
        # Step 2: Generating Embeddings (This step is likely part of analyze_resume now)
        socketio.emit('analysis_progress', {'step': 'embedding', 'message': 'Generating AI Embeddings...'}, namespace='/')
        
        # Step 3: Calculating Similarity (This step is likely part of analyze_resume now)
        socketio.emit('analysis_progress', {'step': 'similarity', 'message': 'Calculating Weighted Similarity...'}, namespace='/')
        
        # Step 4: Analyzing Skill Gaps (This step is likely part of analyze_resume now)
        socketio.emit('analysis_progress', {'step': 'gap', 'message': 'Analyzing Intelligent Skill Gaps...'}, namespace='/')
        
        # Step 5: Generating Recommendations (This step is likely part of analyze_resume now)
        socketio.emit('analysis_progress', {'step': 'recommendation', 'message': 'Generating Strategic Recommendations...'}, namespace='/')
        
        # Step 6: XAI Reasoning (This step is likely part of analyze_resume now)
        socketio.emit('analysis_progress', {'step': 'xai', 'message': 'Analyzing Match Reasoning (XAI)...'}, namespace='/')
        
        # Step 8: Finalizing
        socketio.emit('analysis_progress', {'step': 'finalizing', 'message': 'Finalizing Analytical Report...'}, namespace='/')
        
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
        tech_skills = analysis.get('technical_skills', [])
        soft_skills = analysis.get('soft_skills', [])
        
        for s in tech_skills:
            db.session.add(Skill(resume_id=resume.id, skill_name=s['skill'] if isinstance(s, dict) else s, category='Technical'))
        for s in soft_skills:
            db.session.add(Skill(resume_id=resume.id, skill_name=s['skill'] if isinstance(s, dict) else s, category='Soft'))
        
        db.session.commit()
        
        return jsonify({
            "message": f"Resume ({label}) analyzed successfully",
            "score": analysis.get('resume_score'),
            "breakdown": analysis.get('score_breakdown'),
            "structured": analysis.get('structured_data'),
            "skills": [s['skill'] if isinstance(s, dict) else s for s in tech_skills],
            "technical_skills": tech_skills,
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

    from .. import socketio
    from ..services.resume_service import compare_skills
    
    # Step 2: Generating Embeddings
    socketio.emit('analysis_progress', {'step': 'embedding'}, namespace='/')
    
    # Step 3: Calculating Similarity
    socketio.emit('analysis_progress', {'step': 'similarity'}, namespace='/')
    
    skills = [s.skill_name for s in Skill.query.filter_by(resume_id=latest_resume.id).all()]
    
    # role-specific matching
    fit_report = compare_skills(skills, jd_text, resume_text=latest_resume.extracted_text, role_title=role_title)
    
    # Step 4: Analyzing Skill Gaps
    socketio.emit('analysis_progress', {'step': 'gap'}, namespace='/')
    
    # Step 5: Generating Recommendations
    socketio.emit('analysis_progress', {'step': 'recommendation'}, namespace='/')
    
    # Step 6: XAI Reasoning
    socketio.emit('analysis_progress', {'step': 'xai'}, namespace='/')
    
    # Step 8: Finalizing
    socketio.emit('analysis_progress', {'step': 'finalizing'}, namespace='/')
    
    return jsonify({
        "role": role_title,
        "match_score": fit_report['match_score'],
        "matching_skills": fit_report['matching_skills'],
        "missing_skills": fit_report['missing_skills'],
        "method": fit_report.get('method', 'Cosine Similarity'),
        "insights": fit_report.get('insights', ""),
        "explanation": fit_report.get('explanation', []),
        "recommendations": fit_report.get('recommendations', [])
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
            "method": "Cosine Similarity",
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
