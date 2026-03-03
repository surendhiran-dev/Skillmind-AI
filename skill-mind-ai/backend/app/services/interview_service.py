import random

# Pre-scripted HR interview questions
HR_QUESTIONS = [
    "Tell me about yourself and your professional background.",
    "What are your greatest strengths and how do they relate to this role?",
    "Can you describe a challenging project you've worked on? What was your role?",
    "How do you handle tight deadlines and pressure?",
    "Where do you see yourself in five years?",
    "Why are you interested in this position?",
    "Tell me about a time you had a disagreement with a colleague. How did you resolve it?",
    "What is your approach to learning new technologies?",
    "How do you prioritize tasks when working on multiple projects?",
    "Do you have any questions for us?",
]

# Follow-up questions based on detected topics
FOLLOW_UPS = {
    "team": "That's interesting. Can you elaborate on your experience working in team environments?",
    "lead": "Great leadership experience! How do you motivate your team members?",
    "project": "Tell me more about the outcome of that project. What did you learn?",
    "challenge": "How did you overcome that challenge? What tools or strategies did you use?",
    "learn": "That shows great initiative. What resources do you typically use for learning?",
    "mistake": "Everyone makes mistakes. What was the key takeaway from that experience?",
    "goal": "Those are ambitious goals. What steps are you taking to achieve them?",
    "technical": "Can you dive deeper into the technical aspects of your work?",
}

# Positive and negative sentiment keywords
POSITIVE_WORDS = [
    "excited", "passionate", "love", "enjoy", "great", "excellent", "achieved",
    "accomplished", "successful", "improved", "innovative", "creative", "motivated",
    "dedicated", "enthusiastic", "thrilled", "proud", "proactive", "growth",
    "collaborative", "rewarding", "opportunity", "skilled", "experienced",
]

NEGATIVE_WORDS = [
    "hate", "terrible", "awful", "boring", "difficult", "frustrated", "confused",
    "overwhelmed", "stressed", "failed", "problem", "issue", "struggle", "worst",
    "never", "can't", "impossible", "quit", "fired", "conflict",
]

def analyze_sentiment(text):
    """Simple keyword-based sentiment analysis."""
    text_lower = text.lower()
    
    pos_count = sum(1 for w in POSITIVE_WORDS if w in text_lower)
    neg_count = sum(1 for w in NEGATIVE_WORDS if w in text_lower)
    
    total = pos_count + neg_count
    if total == 0:
        return {"label": "NEUTRAL", "score": 0.5}
    
    pos_ratio = pos_count / total
    
    if pos_ratio > 0.6:
        return {"label": "POSITIVE", "score": min(0.5 + pos_ratio * 0.5, 1.0)}
    elif pos_ratio < 0.4:
        return {"label": "NEGATIVE", "score": max(0.5 - (1 - pos_ratio) * 0.5, 0.0)}
    else:
        return {"label": "NEUTRAL", "score": 0.5}

def get_next_question(question_index):
    """Get the next HR question from the scripted list."""
    if question_index < len(HR_QUESTIONS):
        return HR_QUESTIONS[question_index]
    return None

from .ai_service import call_ai, HAS_AI

def get_ai_response(user_input, context="", question_index=0):
    """
    Generate conversational HR interview response using Gemini.
    Focus on evaluating entry-level potential and academic background.
    """
    if not HAS_AI:
        # Fallback to a simple acknowledgement if no API key
        return {
            "response": "Thank you for sharing that. Can you tell me more about your recent projects?",
            "sentiment": "NEUTRAL",
            "sentiment_score": 0.5
        }

    system_prompt = """
    You are an entry-level HR recruiter.
    Your goal is to conduct a professional, conversational interview for a fresh graduate or intern.
    
    Guidelines:
    1. Analyze the candidate's last response.
    2. Ask ONE logical follow-up question that drills deeper into their projects, academic learning, or foundational skills.
    3. Stay professional and encouraging.
    4. Keep responses concise.
    """
    
    prompt = f"""
    Context: {context}
    Candidate's Last Response: "{user_input}"
    Current Question Index: {question_index}
    
    Provide your response as a JSON object:
    {{
        "response": "Your follow-up question or acknowledgement",
        "sentiment": "POSITIVE|NEGATIVE|NEUTRAL",
        "sentiment_score": 0.0 to 1.0
    }}
    """
    
    response_text = call_ai(prompt, system_prompt)
    if response_text:
        try:
            import json
            clean_json = response_text.replace('```json', '').replace('```', '').strip()
            return json.loads(clean_json)
        except Exception:
            pass
            
    return {
        "response": "Interesting. How did you handle the technical challenges in that situation?",
        "sentiment": "NEUTRAL",
        "sentiment_score": 0.5
    }
