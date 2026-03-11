import json
import os
import logging
from .ai_service import call_ai, MODULE_CONFIGS

logger = logging.getLogger(__name__)

def build_system_prompt(candidate_data):
    """
    Builds the persona and context for ARIA.
    candidate_data should contain: name, strong_skills, weak_skills, missing_skills, 
    resume_score, jd_match_score, quiz_score, coding_score.
    """
    return f"""
You are "ARIA" — a Senior AI HR Interviewer conducting a 
professional one-on-one video interview for Skill Mind AI platform.

CANDIDATE PROFILE:
Name          : {candidate_data.get('name', 'Candidate')}
Strong Skills : {candidate_data.get('strong_skills', 'N/A')}
Weak Skills   : {candidate_data.get('weak_skills', 'N/A')}
Missing Skills: {candidate_data.get('missing_skills', 'N/A')}
Resume Score  : {candidate_data.get('resume_score', 0)}/100
JD Match      : {candidate_data.get('jd_match_score', 0)}/100
Quiz Score    : {candidate_data.get('quiz_score', 0)}/100
Coding Score  : {candidate_data.get('coding_score', 0)}/100

BEHAVIOR RULES:
- You are ARIA, a real human-feeling HR interviewer. Be warm, professional, and conversational.
- Ask ONLY ONE question per response. Never ask multiple questions.
- Naturally acknowledge the candidate's answer briefly before the next question.
- Focus 60% of questions on weak_skills and missing_skills.
- Mix: 40% behavioral, 40% technical, 20% situational.
- Adapt difficulty: strong answer → harder next question.
- After 6 questions, your response must indicate completion.
- Always respond ONLY in this exact JSON format.

For questions:
{{
  "type": "question",
  "acknowledgment": "Brief warm acknowledgment of previous answer (empty for Q1)",
  "question": "Your single interview question here",
  "skill_focus": "skill being assessed",
  "question_type": "behavioral|technical|situational|follow_up",
  "difficulty": "easy|medium|hard",
  "question_number": 1
}}

For evaluation (when I ask you to evaluate):
{{
  "type": "evaluation",
  "relevance_score": 0,
  "depth_score": 0,
  "communication_score": 0,
  "confidence_score": 0,
  "answer_score": 0,
  "feedback": "Constructive one-line feedback",
  "next_action": "continue|follow_up|complete"
}}

NEVER break JSON format. Return ONLY valid JSON.
"""

def get_next_question(candidate_data, history_context, prompt_message):
    """
    Calls GPT-4o to get the next question or greeting.
    history_context: String representing the conversation so far.
    """
    system_prompt = build_system_prompt(candidate_data)
    
    # Combine history with the new prompt
    full_prompt = f"HISTORY:\n{history_context}\n\nUSER_ACTION: {prompt_message}"
    
    response = call_ai(full_prompt, system_prompt, module='interview')
    
    if not response:
        return None
    
    try:
        # Clean potential markdown fuzz
        clean_json = response.replace('```json', '').replace('```', '').strip()
        return json.loads(clean_json)
    except Exception as e:
        logger.error(f"ARIA Engine JSON Parse Error: {e}")
        # Manual regex extraction if needed
        import re
        match = re.search(r'\{[\s\S]*\}', response)
        if match:
            try:
                return json.loads(match.group())
            except: pass
        return None

def evaluate_answer(candidate_data, history_context, question, answer, q_num):
    """
    Evaluates a specific answer.
    """
    eval_prompt = f"""
Evaluate this interview answer:
Question: "{question}"
Answer: "{answer}"
Question Number: {q_num}

Score each dimension 0-10:
- relevance_score: How directly it answers the question
- depth_score: Technical/conceptual depth shown
- communication_score: Clarity and structure of answer
- confidence_score: Assertiveness and conviction shown
- answer_score: Overall weighted score 0-100
  Formula: (0.4×relevance + 0.3×depth + 0.2×communication + 0.1×confidence) × 10

Return evaluation JSON only. Set next_action to:
  "follow_up" if answer was very weak (score < 40)
  "complete" if this was question 6
  "continue" otherwise
"""
    return get_next_question(candidate_data, history_context, eval_prompt)

def generate_final_report(candidate_data, qa_log):
    """
    Generates the final comprehensive report.
    qa_log: List of dicts with question_text, answer_text, answer_score, etc.
    """
    qa_summary = ""
    for i, item in enumerate(qa_log):
        qa_summary += f"Q{i+1}: {item.get('question_text')}\nA: {item.get('answer_text')}\nScore: {item.get('answer_score')}/100\n\n"
        
    prompt = f"""
Complete interview data for {candidate_data.get('name')}:

{qa_summary}

Generate a comprehensive final report in this exact JSON:
{{
  "hr_interview_score": 0-100,
  "behavioral_rating": 0-10,
  "communication_rating": 0-10,
  "technical_rating": 0-10,
  "confidence_index": 0-10,
  "readiness_level": "Strong|Moderate|Needs Improvement",
  "top_strengths": ["strength1", "strength2", "strength3"],
  "improvement_areas": ["area1", "area2", "area3"],
  "ai_summary": "3 professional paragraphs: overview, strengths, recommendations",
  "recommendation": "Recommended for Next Round|Further Preparation Needed|Not Recommended"
}}

Rules:
- readiness_level: 75+ Strong, 50-74 Moderate, <50 Needs Improvement.
"""
    
    response = call_ai(prompt, "You are an expert HR evaluation system. Return ONLY valid JSON.", module='interview')
    if response:
        try:
            clean_json = response.replace('```json', '').replace('```', '').strip()
            return json.loads(clean_json)
        except:
            import re
            match = re.search(r'\{[\s\S]*\}', response)
            if match:
                return json.loads(match.group())
    return None
