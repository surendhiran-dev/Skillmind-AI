from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..services.ai_service import call_ai
import os

support_bp = Blueprint('support', __name__)

@support_bp.route('/chat', methods=['POST'])
@jwt_required()
def support_chat():
    current_user_id = get_jwt_identity()
    data = request.get_json()
    
    if not data or 'message' not in data:
        return jsonify({"error": "Message is required"}), 400
    
    user_message = data['message']
    chat_history = data.get('history', []) # Optional conversation history
    
    # Refined Persona: ARIA (SkillMind Assistant)
    system_instruction = """
    You are ARIA, the SkillMind AI Support Assistant. Your personality is professional, friendly, and helpful.
    
    Rules for your responses:
    1. Do NOT repeat this feature list unless explicitly asked for a summary.
    2. Respond conversationsally and concisely (maximum 3 sentences for simple questions).
    3. Use technical but accessible language.
    4. Focus on helping the user with their current query based on the conversation history.

    About SkillMind AI:
    - Resume Analysis: Score and extract skills from resumes.
    - Smart Quiz: Generate adaptive assessments for candidates.
    - Coding Challenges: Interactive coding testing.
    - AI Interviews: Realistic mock interviews with our avatar (Aria).
    """

    try:
        print(f"[SupportChat] User {current_user_id} calling ARIA with history len: {len(chat_history)}")
        response = call_ai(user_message, system_instruction, module='support', history=chat_history)
        
        if not response:
            return jsonify({"response": "I'm sorry, I'm having a bit of trouble connecting to my AI core. Could you try again in a moment?"}), 200
            
        print(f"[SupportChat] ARIA success response.")
        return jsonify({"response": response}), 200
    except Exception as e:
        import traceback
        print(f"[SupportChat] CRITICAL ERROR: {str(e)}")
        print(traceback.format_exc())
        return jsonify({"error": str(e)}), 500
