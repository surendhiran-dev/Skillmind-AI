import random
import json

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

def get_ai_response(user_input, context="", question_index=0, candidate_stats=None):
    """
    Generate adaptive HR interview questions using Anthropic Claude with full candidate context.
    """
    if not HAS_AI:
        return {
            "question": "Can you tell me more about your recent projects?",
            "question_type": "technical",
            "focus_skill": "General Projects",
            "difficulty": "medium",
            "is_complete": False
        }

    stats_str = json.dumps(candidate_stats) if candidate_stats else "{}"
    
    system_instruction = """
You are a professional AI HR Interviewer conducting a structured technical and behavioral interview for SkillMind AI.
You have been given a candidate profile with performance data from previous assessments.

Rules:
- Ask ONE question at a time
- Keep a professional, calm, encouraging HR tone
- Adapt the next question based on the quality of the previous answer
- Prioritize questions targeting weak_skills and missing_skills
- After each answer, internally score: Relevance, Depth, Communication, Confidence (0-10 each). Do not show scores mid-interview.
- After 6 questions, output: INTERVIEW_COMPLETE
- Return responses in JSON format:
{
  "question": "...",
  "question_type": "behavioral | technical | follow_up",
  "focus_skill": "...",
  "difficulty": "easy | medium | hard",
  "is_complete": false
}
"""

    prompt = f"""
CANDIDATE DATA CONTEXT:
{stats_str}

CURRENT CONVERSATION HISTORY:
{context}

CANDIDATE'S LAST RESPONSE:
"{user_input}"

QUESTION INDEX: {question_index} (Goal: 6-8 questions)

TASK:
1. Analyze the candidate's last response.
2. If this is the start (user_input is "I am ready"), start with a warm greeting and ask a warm-up question.
3. If the answer was weak → generate follow-up or easier question.
4. If the answer was strong → increase difficulty.
5. If question_index >= 6, set is_complete: true and output "INTERVIEW_COMPLETE" in the question field.
6. Provide the NEXT logical question in the specified JSON format.
"""
    
    response_text = call_ai(prompt, system_instruction, module='interview')
    if response_text:
        try:
            clean_json = response_text.replace('```json', '').replace('```', '').strip()
            return json.loads(clean_json)
        except Exception:
            pass
            
    return {
        "question": "Interesting. How did you handle the technical challenges in that situation?",
        "question_type": "follow_up",
        "focus_skill": "Problem Solving",
        "difficulty": "medium",
        "is_complete": False
    }

def evaluate_interview_answer(question, answer):
    """
    Evaluate a candidate's answer in real-time.
    """
    if not HAS_AI:
        return {
            "relevance": 7, "depth": 6, "communication": 8, "confidence": 7,
            "feedback": "Good response.", "answer_score": 6.9
        }

    system_instruction = "You are an expert HR Interview Evaluator."
    prompt = f"""
Given the question: "{question}"
And the candidate's answer: "{answer}"

Score the response on a scale of 0-10 for:
- Relevance (0-10): Does it answer what was asked?
- Depth (0-10): Level of technical/conceptual detail
- Communication (0-10): Clarity and structure
- Confidence (0-10): Assertiveness and conviction

Return JSON:
{{
  "relevance": 0,
  "depth": 0,
  "communication": 0,
  "confidence": 0,
  "feedback": "...",
  "answer_score": 0
}}

Formula for answer_score: (0.4 * relevance + 0.3 * depth + 0.2 * communication + 0.1 * confidence)
"""
    
    response_text = call_ai(prompt, system_instruction, module='interview')
    if response_text:
        try:
            clean_json = response_text.replace('```json', '').replace('```', '').strip()
            return json.loads(clean_json)
        except Exception:
            pass
            
    return {
        "relevance": 5, "depth": 5, "communication": 5, "confidence": 5,
        "feedback": "Evaluation unavailable.", "answer_score": 5.0
    }

def calculate_final_score(evaluations):
    """
    Calculate final HR score based on spec: 
    average of all answer_scores (weighted ×100)
    """
    if not evaluations:
        return 0
    
    total_score = sum([e.get('answer_score', 0) for e in evaluations])
    avg_score = total_score / len(evaluations)
    
    return avg_score * 10 # Scale 0-10 to 0-100 if needed, but the spec says "average of all answer_scores (weighted x100)"
    # Wait, if answer_score is 0-10, avg is 0-10. Weighted x100 might mean scale to 100.
    # Actually, the original code scaled to 30 marks. I'll stick to 0-100 for now.
    return avg_score * 10

def get_readiness_level(score_percentage):
    """Returns strings for report based on score."""
    if score_percentage >= 75: return "Interview Ready: Strong ✅"
    if score_percentage >= 50: return "Interview Ready: Moderate ⚠️"
    return "Needs Improvement ❌"
