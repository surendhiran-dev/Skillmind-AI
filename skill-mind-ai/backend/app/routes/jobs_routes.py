from flask import Blueprint, jsonify, request
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..services.jobs_service import get_recommendations, get_all_jobs, seed_jobs, clear_ai_cache
from ..services.ai_service import generate_dynamic_courses_llm, generate_ai_jobs_llm

jobs_bp = Blueprint('jobs', __name__)

@jobs_bp.route('/recommendations/<int:candidate_id>', methods=['GET'])
@jwt_required()
def recommendations(candidate_id):
    data = get_recommendations(candidate_id)
    if not data:
        return jsonify({"error": "Candidate not found"}), 404
    return jsonify(data), 200

@jobs_bp.route('/all', methods=['GET'])
def all_jobs():
    return jsonify({"jobs": get_all_jobs()}), 200

@jobs_bp.route('/seed', methods=['POST'])
def seed():
    result = seed_jobs()
    return jsonify(result), 200

@jobs_bp.route('/refresh-cache/<int:candidate_id>', methods=['POST'])
@jwt_required()
def refresh_cache(candidate_id):
    """Invalidates the AI jobs cache for a candidate, forcing fresh AI generation."""
    clear_ai_cache(candidate_id)
    return jsonify({"message": "Cache cleared. Next request will generate fresh AI jobs."}), 200

@jobs_bp.route('/ai-courses/<int:candidate_id>', methods=['GET'])
@jwt_required()
def ai_courses(candidate_id):
    """Returns AI-generated dynamic course recommendations based on the candidate's missing skills."""
    data = get_recommendations(candidate_id)
    if not data:
        return jsonify({"error": "Candidate not found"}), 404

    missing_skills = data.get('stats', {}).get('top_missing_skills', [])
    candidate_skills = data.get('candidate', {}).get('skills', [])
    readiness = data.get('candidate', {}).get('readiness_score', 0)

    courses = generate_dynamic_courses_llm(
        missing_skills=missing_skills,
        existing_skills=candidate_skills,
        readiness_score=readiness
    )
    return jsonify({"courses": courses}), 200

@jobs_bp.route('/ai-jobs/<int:candidate_id>', methods=['GET'])
@jwt_required()
def ai_jobs(candidate_id):
    """Returns AI-generated dynamic job listings tailored to the candidate's profile."""
    data = get_recommendations(candidate_id)
    if not data:
        return jsonify({"error": "Candidate not found"}), 404

    candidate = data.get('candidate', {})
    jobs = generate_ai_jobs_llm(
        skills=candidate.get('skills', []),
        readiness_score=candidate.get('readiness_score', 0),
        strong_skills=candidate.get('strong_skills', []),
        weak_skills=candidate.get('weak_skills', [])
    )
    return jsonify({"jobs": jobs}), 200
