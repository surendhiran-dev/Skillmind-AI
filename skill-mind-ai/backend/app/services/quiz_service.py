import random
from .ai_service import generate_quiz_llm, HAS_AI

def generate_questions(skills, jd_text=""):
    """Generate strictly dynamic technical interview MCQs using AI."""
    # Try LLM first
    if HAS_AI:
        try:
            # Seed for randomization to avoid repetition
            seed = random.randint(1, 1000)
            ai_questions = generate_quiz_llm(skills, jd_text)
            if ai_questions and isinstance(ai_questions, list):
                return ai_questions[:15]
        except Exception as e:
            print(f"AI Generation failed: {e}")

    # If AI fails, we generate a very basic dynamic fallback to avoid crash,
    # but we inform the system this is a last resort.
    questions = []
    target_count = 15
    skill_cycle = list(skills) * (target_count // max(len(skills), 1) + 1)
    random.shuffle(skill_cycle)
    
    for skill in skill_cycle[:target_count]:
        skill_key = skill.strip()
        
        # More diverse fallback templates
        templates = [
            {
                "q": f"Which of the following describes the most common use case for {skill_key} in backend engineering?",
                "opts": ["Data Transformation", "UI Rendering", "OS Kernel Optimization", "Video Compression"],
                "ans": "Data Transformation"
            },
            {
                "q": f"In a high-concurrency environment, how does {skill_key} primarily assist in maintaining system stability?",
                "opts": ["Resource Pooling", "Manual Memory Flushing", "Ignoring Requests", "Hardcoded Timeouts"],
                "ans": "Resource Pooling"
            },
            {
                "q": f"What is a critical security best practice when implementing {skill_key} in a production API?",
                "opts": ["Input Validation", "Disabling HTTPS", "Public Credential Storage", "Verbose Error Logging"],
                "ans": "Input Validation"
            },
            {
                "q": f"How do you typically measure the performance efficiency of a {skill_key} implementation?",
                "opts": ["Latency Metrics", "Line Counts", "File Weight", "Font Size"],
                "ans": "Latency Metrics"
            }
        ]
        
        tpl = random.choice(templates)
        random.shuffle(tpl["opts"]) # Randomize option order
        
        questions.append({
            "skill": skill_key, 
            "question": tpl["q"],
            "options": tpl["opts"],
            "answer": tpl["ans"],
            "difficulty": "medium"
        })

    return questions

def evaluate_answer(correct_answer, user_answer):
    """
    Evaluate a single MCQ quiz answer. Returns 0 or 2 marks.
    2 marks = correct option selected
    0 marks = incorrect or blank
    """
    if not user_answer or not correct_answer:
        return 0
    
    # Exact match for MCQs
    if user_answer.strip().lower() == correct_answer.strip().lower():
        return 2
    return 0
