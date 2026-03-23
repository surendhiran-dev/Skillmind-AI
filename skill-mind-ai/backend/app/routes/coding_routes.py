from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..services.coding_service import (
    check_syntax, evaluate_code_quality,
    run_test_cases, get_all_problems, get_problem_by_id,
    get_challenge_set
)
from ..services.scoring_service import refresh_user_score
from ..models.models import CodingTest, db
import random

coding_bp = Blueprint('coding', __name__)


@coding_bp.route('/problems', methods=['GET', 'POST'])
@jwt_required()
def list_problems():
    """Return the list of all coding problems (no test cases). Filter by JD if provided."""
    jd_text = request.args.get('jd', '') or (request.get_json() or {}).get('jd', '')
    return jsonify({"problems": get_all_problems(jd_text)}), 200


@coding_bp.route('/challenge-set', methods=['POST', 'GET'])
@jwt_required()
def challenge_set():
    """Return 6 random coding problems: 2 easy, 2 medium, 2 hard.
    Each problem carries 5 marks (total 30).
    Problems are shuffled each time to avoid repetition."""
    data = request.get_json() or {}
    jd_text = data.get('jd', '')
    res = get_challenge_set(jd_text)
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

    is_valid, syntax_msg = check_syntax(code)
    quality = evaluate_code_quality(code)
    test_results, test_score = run_test_cases(code, problem_id)

    if is_valid:
        final_score = round(0.7 * test_score + 0.3 * quality["score"])
    else:
        final_score = 0

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
    db.session.commit()

    # Convert final_score (0-100) to marks out of 5
    if final_score >= 80:
        marks = 5
    elif final_score >= 60:
        marks = 4
    elif final_score >= 40:
        marks = 3
    elif final_score >= 20:
        marks = 2
    elif final_score > 0:
        marks = 1
    else:
        marks = 0

    return jsonify({
        "is_valid": is_valid,
        "syntax_message": syntax_msg,
        "test_results": test_results,
        "test_score": test_score,
        "quality_report": quality,
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
        
        is_valid, _ = check_syntax(code)
        quality = evaluate_code_quality(code)
        test_results, test_score = run_test_cases(code, problem_id)
        
        if is_valid:
            final_score = round(0.7 * test_score + 0.3 * quality["score"])
        else:
            final_score = 0
        
        if final_score >= 80:
            marks = 5
        elif final_score >= 60:
            marks = 4
        elif final_score >= 40:
            marks = 3
        elif final_score >= 20:
            marks = 2
        elif final_score > 0:
            marks = 1
        else:
            marks = 0
        
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
