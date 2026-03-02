from flask import request
from flask_socketio import emit
from .. import socketio
from ..services.interview_service import get_ai_response
from ..models.models import HRSession, db

# Context storage (simple in-memory for demo)
user_contexts = {}
user_question_indices = {}

@socketio.on('connect')
def handle_connect():
    print(f"Client connected: {request.sid}")

@socketio.on('start_interview')
def handle_start(data):
    user_id = data.get('user_id', request.sid)
    user_contexts[user_id] = ""
    user_question_indices[user_id] = 0
    emit('ai_message', {
        'message': "Hello! I'm your AI interviewer from Skill Mind. Let's begin. Tell me about yourself and your professional background.",
        'sentiment': 'NEUTRAL'
    })

@socketio.on('user_message')
def handle_message(data):
    user_id = data.get('user_id', request.sid)
    message = data.get('message', '')
    
    context = user_contexts.get(user_id, "")
    q_index = user_question_indices.get(user_id, 0) + 1
    user_question_indices[user_id] = q_index
    
    result = get_ai_response(message, context, question_index=q_index)
    
    # Update context
    user_contexts[user_id] += f"\nUser: {message}\nAI: {result['response']}"
    
    emit('ai_message', {
        'message': result['response'],
        'sentiment': result['sentiment'],
        'sentiment_score': result['sentiment_score']
    })

@socketio.on('end_interview')
def handle_end(data):
    user_id = data.get('user_id', request.sid)
    # Cleanup
    user_contexts.pop(user_id, None)
    user_question_indices.pop(user_id, None)
    emit('interview_ended', {'message': 'Interview session ended.'})

@socketio.on('disconnect')
def handle_disconnect():
    print(f"Client disconnected: {request.sid}")
