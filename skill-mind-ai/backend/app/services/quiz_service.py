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
                return ai_questions[:30]
        except Exception as e:
            print(f"AI Generation failed: {e}")

    # If AI fails, we generate a very basic dynamic fallback to avoid crash,
    # but we inform the system this is a last resort.
    questions = []
    target_count = 30
    skill_cycle = list(skills) * (target_count // max(len(skills), 1) + 1)
    random.shuffle(skill_cycle)
    
    # Advanced fallback rotation
    templates_pool = [
        {"q": "Scenario: A mission-critical system using {} is experiencing intermittent latency. What is the first diagnostic step?", "opts": ["Trace system calls", "Restart server", "Increase RAM", "Delete logs"], "ans": "Trace system calls"},
        {"q": "How does {} handle race conditions in high-frequency transaction environments?", "opts": ["Mutex/Locking", "Ignore concurrency", "Restart process", "Standard Delay"], "ans": "Mutex/Locking"},
        {"q": "When optimizing {} for performance, which metric is most significant for throughput?", "opts": ["I/O Throughput", "Source Code size", "Color Scheme", "Compiler Name"], "ans": "I/O Throughput"},
        {"q": "Security: Which of the following is a known vulnerability when implementing {} without proper input sanitization?", "opts": ["Injection Attacks", "File Compression", "User Logout", "Dark Mode failure"], "ans": "Injection Attacks"},
        {"q": "Which design pattern is best suited for implementing a scalable architecture with {}?", "opts": ["Microservices", "Monolithic", "MVC", "Factory Pattern"], "ans": "Microservices"},
        {"q": "For a production-grade deployment using {}, which CI/CD strategy is most reliable?", "opts": ["Blue-Green", "Manual Upload", "Direct Edit", "Flash Drive"], "ans": "Blue-Green"}
    ]
    
    for i, skill in enumerate(skill_cycle[:target_count]):
        skill_key = skill.strip()
        tpl = templates_pool[i % len(templates_pool)]
        
        # Format the question with the skill
        question_text = tpl["q"].format(skill_key)
        opts = list(tpl["opts"])
        random.shuffle(opts)
        
        questions.append({
            "skill": skill_key, 
            "question": question_text,
            "options": opts,
            "answer": tpl["ans"],
            "difficulty": "medium"
        })

    return questions

def evaluate_answer(correct_answer, user_answer):
    """
    Evaluate a single MCQ quiz answer. Returns 0 or 1 marks.
    1 marks = correct option selected
    0 marks = incorrect or blank
    """
    if not user_answer or not correct_answer:
        return 0
    
    # Exact match for MCQs
    if user_answer.strip().lower() == correct_answer.strip().lower():
        return 1
    return 0
