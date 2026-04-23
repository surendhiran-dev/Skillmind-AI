from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..services.coding_service import (
    check_syntax, evaluate_code_quality,
    run_test_cases, get_all_problems, get_problem_by_id,
    get_challenge_set, get_ai_coding_analysis, calculate_comprehensive_score
)
from ..services.scoring_service import refresh_user_score
from ..models.models import CodingTest, Resume, Skill, db
import random

coding_bp = Blueprint('coding', __name__)


@coding_bp.route('/problems', methods=['GET', 'POST'])
@jwt_required()
def list_problems():
    """Return a placeholder or info about dynamic generation."""
    return jsonify({
        "message": "Skill-Mind AI now generates unique, real-time challenges based on your resume. Start an assessment to see them!",
        "type": "dynamic"
    }), 200


@coding_bp.route('/challenge-set', methods=['POST', 'GET'])
@jwt_required()
def challenge_set():
    """Return 6 random coding problems: 2 easy, 2 medium, 2 hard.
    Each problem carries 5 marks (total 30).
    Problems are shuffled each time to avoid repetition."""
    data = request.get_json() or {}
    jd_text = data.get('jd', '')
    
    # Fetch User's Resume Context
    user_id = int(get_jwt_identity())
    resume = Resume.query.filter_by(user_id=user_id).order_by(Resume.uploaded_at.desc()).first()
    resume_data = {}
    if resume:
        skills = [s.skill_name for s in Skill.query.filter_by(resume_id=resume.id).all()]
        resume_data = {
            "user_id": user_id,
            "extracted_text": resume.extracted_text,
            "skills": skills,
            "structured_data": resume.structured_data
        }
    
    res = get_challenge_set(jd_text, resume_data)
    challenges = res["challenges"]
    detected_languages = res["languages"]
    
    # Return problems without test cases (for security)
    safe_challenges = []
    for p in challenges:
        safe_challenges.append({
            "id": p["id"],
            "title": p["title"],
            "difficulty": p["difficulty"],
            "description": p["description"],
            "examples": p.get("examples", []),
            "hints": p.get("hints", []),
            "language": p.get("language", "python"),
            "starter_code": p["starter_code"],
            "max_marks": 5
        })
    
    return jsonify({
        "challenges": safe_challenges,
        "languages": detected_languages,
        "total_questions": len(safe_challenges),
        "marks_per_question": 5,
        "total_marks": 30
    }), 200


@coding_bp.route('/problems/<int:problem_id>', methods=['GET'])
@jwt_required()
def get_problem(problem_id):
    """Return a single problem by ID."""
    problem = get_problem_by_id(problem_id)
    if not problem:
        return jsonify({"message": "Problem not found"}), 404

    return jsonify({
        "id": problem["id"],
        "title": problem["title"],
        "difficulty": problem["difficulty"],
        "description": problem["description"],
        "examples": problem["examples"],
        "hints": problem["hints"],
        "language": problem.get("language", "python"),
        "starter_code": problem["starter_code"],
    }), 200


@coding_bp.route('/submit', methods=['POST'])
@jwt_required()
def submit_code():
    data = request.get_json()
    if not data:
        return jsonify({"message": "No input data provided"}), 400

    user_id = int(get_jwt_identity())
    code = data.get('code', '').strip()
    problem_id = data.get('problem_id', 1)

    if not code:
        return jsonify({"message": "No code provided"}), 400

    language = data.get('language', 'python').lower()
    
    # Initialize variables to prevent UnboundLocalError
    test_results = []
    test_score = 0
    quality = {"score": 0, "feedback": "Evaluation skipped."}
    is_valid = True
    syntax_msg = ""
    
    # Verify language against problem
    problem = get_problem_by_id(problem_id)
    problem_title = problem["title"] if problem else f"Problem {problem_id}"

    if problem and problem.get('language') != language:
        is_valid = False
        syntax_msg = f"Language Mismatch: Question requires {problem.get('language')}, but you submitted {language}."
        test_score = 0
        quality = {"score": 0, "feedback": syntax_msg}
    if is_valid:
        test_results, test_score, exec_time = run_test_cases(code, problem_id, language)
        quality = evaluate_code_quality(code, language, problem_title=problem_title)
        
        # New Perfect Analysis (Deep AI Insights)
        ai_analysis = get_ai_coding_analysis(code, language, problem, test_results)
        
        # Comprehensive weighted scoring
        final_score = calculate_comprehensive_score(test_score, quality, ai_analysis)
    else:
        test_results = []
        test_score = 0
        exec_time = 0
        quality = {"score": 0, "feedback": "Syntax error prevented evaluation."}
        ai_analysis = {"logic_overview": "Evaluation skipped.", "bug_analysis": syntax_msg, "suggestions": ["Fix the syntax error first."]}
        final_score = 0

    # Marks logic: 1-5 scale mapped to final_score
    # 90+ = 5, 75+ = 4, 55+ = 3, 35+ = 2, 10+ = 1
    if final_score >= 90: marks = 5
    elif final_score >= 75: marks = 4
    elif final_score >= 55: marks = 3
    elif final_score >= 35: marks = 2
    elif final_score >= 10: marks = 1
    else: marks = 0

    # Persist the test
    new_test = CodingTest(
        user_id=user_id,
        problem_statement=problem_title,
        submitted_code=code,
        score=final_score,
        quality_report={
            "quality": quality,
            "ai_analysis": ai_analysis,
            "exec_time": exec_time,
            "test_score": test_score
        }
    )
    db.session.add(new_test)
    db.session.commit()

    try:
        refresh_user_score(user_id)
    except: pass

    return jsonify({
        "is_valid": is_valid,
        "syntax_message": syntax_msg,
        "test_results": test_results,
        "test_score": test_score,
        "execution_time_ms": exec_time,
        "expert_report": ai_analysis,
        "quality_metrics": quality.get('details', {}),
        "final_score": final_score,
        "marks": marks,
        "max_marks": 5,
        "problem_title": problem_title,
    }), 200


@coding_bp.route('/submit-all', methods=['POST'])
@jwt_required()
def submit_all_coding():
    """Submit all 6 coding solutions at once and return total marks."""
    data = request.get_json()
    if not data:
        return jsonify({"message": "No input data provided"}), 400

    user_id = int(get_jwt_identity())
    submissions = data.get('submissions', [])
    
    if not submissions:
        return jsonify({"message": "No submissions provided"}), 400

    total_marks = 0
    results = []
    
    max_total = 30 # 6 questions * 5 marks
    
    
    for sub in submissions:
        code = sub.get('code', '').strip()
        problem_id = sub.get('problem_id', 1)
        
        if not code:
            results.append({"problem_id": problem_id, "marks": 0, "max_marks": 5, "skipped": True})
            continue
        
        language = sub.get('language', 'python').lower()
        
        # Verify language against problem
        problem = get_problem_by_id(problem_id)
        problem_title = problem["title"] if problem else f"Problem {problem_id}"

        if problem and problem.get('language') != language:
            is_valid = False
            test_score = 0
            quality = {"score": 0, "feedback": f"Language Mismatch: Question requires {problem.get('language')}"}
        else:
            is_valid, _ = check_syntax(code, language)
            quality = evaluate_code_quality(code, language, problem_title=problem_title)
            test_results, test_score = run_test_cases(code, problem_id, language)
        
        if is_valid:
            final_score = round(0.7 * test_score + 0.3 * quality["score"])
        else:
            final_score = 0
        
        # Marks calculation with Logic Gate
        tmp_marks = 0
        if final_score >= 81: tmp_marks = 5
        elif final_score >= 61: tmp_marks = 4
        elif final_score >= 41: tmp_marks = 3
        elif final_score >= 21: tmp_marks = 2
        elif final_score > 0: tmp_marks = 1
        
        if test_score < 20:
            marks = min(tmp_marks, 1)
        else:
            marks = tmp_marks
        
        total_marks += marks
        
        problem = get_problem_by_id(problem_id)
        problem_title = problem["title"] if problem else f"Problem {problem_id}"
        
        new_test = CodingTest(
            user_id=user_id,
            problem_statement=problem_title,
            submitted_code=code,
            score=final_score,
            quality_report=quality,
        )
        db.session.add(new_test)
        
        results.append({
            "problem_id": problem_id,
            "problem_title": problem_title,
            "marks": marks,
            "max_marks": 5,
            "final_score": final_score,
            "skipped": False
        })
    
    
    score_pct = (total_marks / max_total * 100) if max_total > 0 else 0
    
    # Final summary record for statistics/reports
    summary_test = CodingTest(
        user_id=user_id,
        problem_statement="Full Assessment Summary",
        submitted_code=f"Completed {len(submissions)} challenges.",
        score=round(score_pct),
        quality_report={"total_marks": total_marks, "max_marks": 30, "details": results}
    )
    db.session.add(summary_test)
    db.session.commit()
    
    # Update unified score
    try:
        refresh_user_score(user_id)
    except: pass
    
    return jsonify({
        "message": "All coding challenges submitted",
        "total_marks": total_marks,
        "max_marks": 30,
        "score_pct": round(score_pct, 1),
        "results": results
    }), 200
