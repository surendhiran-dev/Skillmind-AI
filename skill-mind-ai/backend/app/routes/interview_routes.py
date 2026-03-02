from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..services.interview_service import get_ai_response, get_next_question, analyze_sentiment
from ..models.models import HRSession, db

interview_bp = Blueprint('interview', __name__)

# In-memory interview state (per user)
interview_sessions = {}

@interview_bp.route('/start', methods=['POST'])
@jwt_required()
def start_interview():
    user_id = int(get_jwt_identity())
    data = request.get_json() or {}
    jd_text = data.get('jd', '')
    
    interview_sessions[user_id] = {
        "question_index": 0,
        "conversation": [],
        "sentiments": [],
        "jd": jd_text
    }
    
    # Customize intro if JD is present
    if jd_text:
        from ..services.resume_service import analyze_resume
        jd_analysis = analyze_resume(jd_text)
        jd_skills = ", ".join(jd_analysis['skills'][:3]) if jd_analysis['skills'] else "the required skills"
        first_question = f"Hello! I'm your AI interviewer. I've reviewed the job requirements which highlight {jd_skills}. To start, how would you describe your experience in these areas?"
    else:
        first_question = "Hello! I'm your AI interviewer from Skill Mind. Let's begin the interview. Tell me about yourself and your professional background."
        
    interview_sessions[user_id]["conversation"].append({"role": "ai", "message": first_question})
    
    return jsonify({
        "message": first_question,
        "sentiment": "NEUTRAL"
    }), 200

@interview_bp.route('/respond', methods=['POST'])
@jwt_required()
def respond():
    user_id = int(get_jwt_identity())
    data = request.get_json()
    user_message = data.get('message', '')
    
    if user_id not in interview_sessions:
        return jsonify({"message": "Please start an interview first"}), 400
    
    session = interview_sessions[user_id]
    session["question_index"] += 1
    session["conversation"].append({"role": "user", "message": user_message})
    
    result = get_ai_response(user_message, question_index=session["question_index"])
    
    session["conversation"].append({"role": "ai", "message": result["response"]})
    session["sentiments"].append(result["sentiment_score"])
    
    is_complete = session["question_index"] >= 10
    
    return jsonify({
        "message": result["response"],
        "sentiment": result["sentiment"],
        "sentiment_score": result["sentiment_score"],
        "is_complete": is_complete
    }), 200

@interview_bp.route('/end', methods=['POST'])
@jwt_required()
def end_interview():
    user_id = int(get_jwt_identity())
    
    if user_id not in interview_sessions:
        return jsonify({"message": "No active interview session"}), 400
    
    session = interview_sessions[user_id]
    data = request.get_json() or {}
    duration = data.get('duration', 0)
    
    # Calculate average sentiment score
    avg_sentiment = sum(session["sentiments"]) / len(session["sentiments"]) if session["sentiments"] else 0.5
    
    # Save to database
    from datetime import datetime
    interview = HRSession(
        user_id=user_id,
        conversation_history=session["conversation"],
        sentiment_score=avg_sentiment,
        final_feedback=f"Interview completed. Average sentiment score: {avg_sentiment:.2f}"
    )
    db.session.add(interview)
    db.session.commit()
    
    # Cleanup
    del interview_sessions[user_id]
    
    return jsonify({
        "message": "Interview completed! Your responses have been analyzed.",
        "sentiment_score": avg_sentiment,
        "feedback": f"Overall sentiment: {'Positive' if avg_sentiment > 0.6 else 'Neutral' if avg_sentiment > 0.4 else 'Needs improvement'}",
        "interview_id": interview.id
    }), 200
