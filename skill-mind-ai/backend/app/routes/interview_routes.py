from flask import Blueprint, request, jsonify
from .. import db
from ..models.models import User, Resume, Score, InterviewSession, InterviewQA, InterviewReport
from ..services.interview_engine import get_next_question, evaluate_answer, generate_final_report
from ..services.scoring_service import refresh_user_score
import secrets
from datetime import datetime
import json

interview_bp = Blueprint('interview', __name__)

# Helper to get candidate context
def get_candidate_data(user_id):
    """Helper to get candidate context, handles both int and clerk-style string IDs."""
    if not user_id:
        return None
        
    # Handle clerk-style IDs if they are just prefixed integers
    if isinstance(user_id, str) and user_id.startswith('user_'):
        try:
            # Try to extract integer if it's 'user_123'
            user_id = int(user_id.replace('user_', ''))
        except (ValueError, TypeError):
            # If it's a UUID/Hash from Clerk, we'd need a mapping table.
            # For now, let's try to find by username or email if we had that, 
            # but here we only have user_id.
            pass

    # Fetch from models
    try:
        user = User.query.get(user_id)
        if not user:
            # Fallback: try to find by some other field if user_id is a string
            if isinstance(user_id, str):
                user = User.query.filter((User.username == user_id) | (User.email == user_id)).first()
            
        if not user:
            return None
            
        resume = Resume.query.filter_by(user_id=user.id).order_by(Resume.uploaded_at.desc()).first()
        score = Score.query.filter_by(user_id=user.id).order_by(Score.generated_at.desc()).first()
            
        return {
            "name": user.username,
            "strong_skills": json.dumps(resume.skill_confidence) if resume and resume.skill_confidence else "N/A",
            "weak_skills": json.dumps(score.skill_gaps) if score and score.skill_gaps else "N/A",
            "missing_skills": "N/A",
            "resume_score": resume.resume_score if resume else 0,
            "jd_match_score": score.final_score if score else 0,
            "quiz_score": score.quiz_score if score else 0,
            "coding_score": score.coding_score if score else 0
        }
    except Exception as e:
        print(f"Error fetching candidate data for {user_id}: {e}")
        return None

@interview_bp.route('/start', methods=['POST'])
def start_interview():
    data = request.json
    user_id = data.get('user_id') # In our existing app, we use user_id
    
    candidate_data = get_candidate_data(user_id)
    if not candidate_data:
        return jsonify({'error': 'Candidate not found'}), 404
        
    token = secrets.token_hex(32)
    session = InterviewSession(
        user_id=user_id,
        session_token=token,
        status='started',
        total_questions=6
    )
    db.session.add(session)
    db.session.commit()
    
    # Greetings from ARIA
    history = ""
    try:
        aria_response = get_next_question(
            candidate_data, 
            history, 
            "Begin the interview. Greet the candidate warmly by name, introduce yourself as ARIA, briefly explain the interview structure (6 questions), then ask your first question."
        )
    except Exception as e:
        print(f"ARIA Generation Error: {e}")
        return jsonify({'error': 'ARIA failed to generate greeting', 'details': str(e)}), 500
    
    if not aria_response:
        return jsonify({'error': 'ARIA returned empty response'}), 500
        
    session.current_question = 1
    db.session.commit()
    
    return jsonify({
        'token': token,
        'session_id': session.id,
        'response': aria_response
    })

@interview_bp.route('/answer', methods=['POST'])
def submit_answer():
    data = request.json
    token = data.get('token')
    answer = data.get('answer', '').strip()
    
    session = InterviewSession.query.filter_by(session_token=token).first()
    if not session:
        return jsonify({'error': 'Session not found'}), 404
    if not answer:
        return jsonify({'error': 'Answer is empty'}), 400
        
    candidate_data = get_candidate_data(session.user_id)
    
    # Load history from QA log
    qa_history_items = InterviewQA.query.filter_by(session_id=session.id).order_by(InterviewQA.question_number).all()
    history_str = ""
    for item in qa_history_items:
        history_str += f"Q: {item.question_text}\nA: {item.answer_text}\n"
        
    # Get the question text from the last QA item or session state
    # If no QA items, this was Q1
    current_q_num = session.current_question
    last_q_text = ""
    if qa_history_items:
        # This shouldn't really happen if we follow the flow correctly
        # Actually, we need the question that the user just answered.
        # Let's assume the frontend sends the question text or we store it in session.
        # A better way is to store the "pending" question in the Session model.
        pass
    
    # For now, let's just use the answer and evaluate
    # EVALUATION
    # We need to know what question was asked.
    # Let's add 'last_question_text' to InterviewSession or get it from the frontend.
    last_q_text = data.get('question_text', '') 
    
    try:
        eval_result = evaluate_answer(candidate_data, history_str, last_q_text, answer, current_q_num)
    except Exception as e:
        print(f"ARIA Evaluation Error: {e}")
        return jsonify({'error': 'ARIA evaluation service error', 'details': str(e)}), 500
    
    if not eval_result:
        return jsonify({'error': 'ARIA failed to produce evaluation'}), 500
        
    # SAVE QA
    qa = InterviewQA(
        session_id=session.id,
        question_number=current_q_num,
        question_text=last_q_text,
        skill_focus=eval_result.get('skill_focus', 'N/A'),
        question_type=eval_result.get('question_type', 'technical'),
        difficulty=eval_result.get('difficulty', 'medium'),
        answer_text=answer,
        relevance_score=eval_result.get('relevance_score', 0),
        depth_score=eval_result.get('depth_score', 0),
        communication_score=eval_result.get('communication_score', 0),
        confidence_score=eval_result.get('confidence_score', 0),
        answer_score=eval_result.get('answer_score', 0),
        ai_feedback=eval_result.get('feedback', ''),
        answered_at=datetime.utcnow()
    )
    db.session.add(qa)
    
    next_action = eval_result.get('next_action', 'continue')
    
    if next_action == 'complete' or current_q_num >= 6:
        # Generate final report
        qa_log = InterviewQA.query.filter_by(session_id=session.id).all()
        # Add the one we just created
        qa_log.append(qa)
        
        report_data = generate_final_report(candidate_data, [
            {
                'question_text': q.question_text,
                'answer_text': q.answer_text,
                'question_type': q.question_type,
                'answer_score': q.answer_score
            } for q in qa_log
        ])
        
        if report_data:
            report = InterviewReport(
                session_id=session.id,
                hr_interview_score=report_data.get('hr_interview_score', 0),
                behavioral_rating=report_data.get('behavioral_rating', 0),
                communication_rating=report_data.get('communication_rating', 0),
                technical_rating=report_data.get('technical_rating', 0),
                confidence_index=report_data.get('confidence_index', 0),
                readiness_level=report_data.get('readiness_level', 'Moderate'),
                top_strengths=",".join(report_data.get('top_strengths', [])),
                improvement_areas=",".join(report_data.get('improvement_areas', [])),
                ai_summary=report_data.get('ai_summary', ''),
                recommendation=report_data.get('recommendation', '')
            )
            db.session.add(report)
            
        session.status = 'completed'
        session.ended_at = datetime.utcnow()
        db.session.commit()
        
        # Trigger unified score update for the dashboard
        try:
            refresh_user_score(session.user_id)
        except Exception as e:
            print(f"Error refreshing user score: {e}")
        
        return jsonify({
            'status': 'complete',
            'evaluation': eval_result,
            'report': report_data
        })
    
    # NEXT QUESTION
    session.current_question += 1
    db.session.commit()
    
    # Add new answer to history for the next question prompt
    history_str += f"Q: {last_q_text}\nA: {answer}\n"
    next_q = get_next_question(candidate_data, history_str, "Proceed with the next interview question.")
    
    return jsonify({
        'status': 'continue',
        'evaluation': eval_result,
        'next_question': next_q,
        'question_number': session.current_question
    })

@interview_bp.route('/report/<int:session_id>', methods=['GET'])
def get_report(session_id):
    report = InterviewReport.query.filter_by(session_id=session_id).first()
    qa_log = InterviewQA.query.filter_by(session_id=session_id).order_by(InterviewQA.question_number).all()
    
    if not report:
        return jsonify({'error': 'Report not found'}), 404
        
    return jsonify({
        'report': {
            'hr_interview_score': report.hr_interview_score,
            'behavioral_rating': report.behavioral_rating,
            'communication_rating': report.communication_rating,
            'technical_rating': report.technical_rating,
            'confidence_index': report.confidence_index,
            'readiness_level': report.readiness_level,
            'top_strengths': report.top_strengths.split(',') if report.top_strengths else [],
            'improvement_areas': report.improvement_areas.split(',') if report.improvement_areas else [],
            'ai_summary': report.ai_summary,
            'recommendation': report.recommendation
        },
        'qa_log': [
            {
                'question': q.question_text,
                'answer': q.answer_text,
                'score': q.answer_score,
                'feedback': q.ai_feedback
            } for q in qa_log
        ]
    })
