from flask import request
from flask_socketio import emit
from .. import socketio
from ..services.interview_service import get_ai_response
from ..models.models import db
import json

# Context storage
user_contexts = {}

@socketio.on('connect')
def handle_connect():
    print(f"Client connected: {request.sid}")

@socketio.on('start_interview')
def handle_start(data):
    user_id = data.get('user_id')
    if not user_id: return
    
    from ..routes.interview_routes import get_candidate_context
    stats = get_candidate_context(user_id)
    
    user_contexts[user_id] = {
        "history": [],
        "q_index": 0,
        "stats": stats,
        "evaluations": []
    }
    
    res = get_ai_response("Start", "", 0, stats)
    user_contexts[user_id]["history"].append({"role": "ai", "message": res['response']})
    
    emit('ai_message', {
        'message': res['response'],
        'evaluation': res.get('evaluation'),
        'sentiment': res.get('sentiment')
    })

@socketio.on('user_message')
def handle_message(data):
    user_id = data.get('user_id')
    message = data.get('message', '')
    if user_id not in user_contexts: return

    ctx = user_contexts[user_id]
    ctx["history"].append({"role": "user", "message": message})
    
    history_str = "\n".join([f"{m['role']}: {m['message']}" for m in ctx["history"][-4:]])
    res = get_ai_response(message, history_str, ctx["q_index"], ctx["stats"])
    
    ctx["history"].append({"role": "ai", "message": res['response']})
    ctx["evaluations"].append(res.get('evaluation', {}))
    ctx["q_index"] += 1
    
    emit('ai_message', {
        'message': res['response'],
        'evaluation': res.get('evaluation'),
        'sentiment': res.get('sentiment'),
        'is_complete': ctx["q_index"] >= 5
    })

@socketio.on('end_interview')
def handle_end(data):
    user_id = data.get('user_id')
    user_contexts.pop(user_id, None)
    emit('interview_ended', {'message': 'Interview session ended.'})

@socketio.on('disconnect')
def handle_disconnect():
    print(f"Client disconnected: {request.sid}")
