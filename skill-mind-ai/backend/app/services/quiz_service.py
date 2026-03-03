import random
from .ai_service import generate_quiz_llm, HAS_AI

# Pre-built question bank organized by skill and difficulty
QUESTION_BANK = {
    "Python": [
        {"q": "What are Python decorators and how do they work? Give an example.", "d": "medium"},
        {"q": "Explain the difference between a list and a tuple in Python.", "d": "easy"},
        {"q": "What is the GIL (Global Interpreter Lock) in Python and how does it affect multi-threading?", "d": "hard"},
        {"q": "How does Python's garbage collection work?", "d": "hard"},
        {"q": "What are generators in Python and when would you use them?", "d": "medium"},
        {"q": "Explain the difference between deepcopy and shallow copy in Python.", "d": "easy"},
        {"q": "What is a context manager in Python and how do you implement one?", "d": "medium"},
        {"q": "Explain the use of *args and **kwargs in functions.", "d": "easy"},
        {"q": "How do you handle memory management in Python?", "d": "hard"},
    ],
    "JavaScript": [
        {"q": "Explain closures in JavaScript with an example.", "d": "medium"},
        {"q": "What is the difference between 'let', 'const', and 'var'?", "d": "easy"},
        {"q": "How does the event loop work in JavaScript?", "d": "hard"},
        {"q": "What are Promises and how do they differ from callbacks?", "d": "medium"},
        {"q": "Explain prototypal inheritance in JavaScript.", "d": "hard"},
        {"q": "What is the difference between '==' and '===' in JavaScript?", "d": "easy"},
        {"q": "Explain the 'this' keyword in different contexts.", "d": "medium"},
        {"q": "What is Hoisting in JavaScript?", "d": "easy"},
        {"q": "Explain the difference between async/await and traditional Promises.", "d": "medium"},
    ],
    "SQL": [
        {"q": "What is the difference between INNER JOIN and LEFT JOIN?", "d": "easy"},
        {"q": "Explain database normalization and its different forms.", "d": "medium"},
        {"q": "What are indexes and how do they improve query performance?", "d": "medium"},
        {"q": "What is a stored procedure and when would you use one?", "d": "medium"},
        {"q": "Explain the ACID properties of database transactions.", "d": "hard"},
        {"q": "What is the difference between WHERE and HAVING clauses?", "d": "easy"},
        {"q": "Explain the difference between a primary key and a unique key.", "d": "easy"},
        {"q": "What is a window function in SQL?", "d": "hard"},
        {"q": "How do you optimize a slow SQL query?", "d": "hard"},
    ],
    "React": [
        {"q": "What are React hooks and why were they introduced?", "d": "easy"},
        {"q": "Explain the virtual DOM and how React uses it for rendering.", "d": "medium"},
        {"q": "What is the difference between state and props in React?", "d": "easy"},
        {"q": "How does useEffect work and what are its common use cases?", "d": "medium"},
        {"q": "What is React context and when should you use it instead of Redux?", "d": "medium"},
        {"q": "Explain the lifecycle methods in class components vs functional components.", "d": "medium"},
        {"q": "What is React.memo and when should you use it?", "d": "hard"},
        {"q": "Explain the reconciliation algorithm in React.", "d": "hard"},
    ],
    "Java": [
        {"q": "What is the difference between an abstract class and an interface in Java?", "d": "easy"},
        {"q": "Explain Java's garbage collection mechanism.", "d": "hard"},
        {"q": "What are the main principles of Object-Oriented Programming?", "d": "easy"},
        {"q": "What is multithreading in Java and how do you handle synchronization?", "d": "medium"},
        {"q": "Explain the difference between HashMap and TreeMap.", "d": "medium"},
        {"q": "What is the diamond problem in Java and how is it resolved?", "d": "hard"},
        {"q": "Explain the Java Memory Model (Stack vs Heap).", "d": "hard"},
    ],
    "Docker": [
        {"q": "What is the difference between a Docker image and a container?", "d": "easy"},
        {"q": "How do you optimize a Dockerfile for smaller image sizes?", "d": "medium"},
        {"q": "Explain Docker Compose and its use cases.", "d": "easy"},
        {"q": "What are Docker volumes and why are they important?", "d": "medium"},
        {"q": "How do multi-stage builds work in Docker?", "d": "hard"},
    ],
}

# Generic fallback questions
GENERIC_QUESTIONS = [
    {"q": "Explain the core concepts and best practices of {skill}.", "d": "easy"},
    {"q": "Describe a project where you used {skill}. What challenges did you face?", "d": "medium"},
    {"q": "What are the advantages and disadvantages of using {skill}?", "d": "medium"},
    {"q": "How would you explain {skill} to someone with no technical background?", "d": "easy"},
    {"q": "What are the latest trends or updates in {skill}?", "d": "hard"},
]

def generate_questions(skills, jd_text=""):
    """Generate technical interview questions using AI (Gemini) or a hardcoded fallback."""
    # Try LLM first
    if HAS_AI:
        try:
            ai_questions = generate_quiz_llm(skills, jd_text)
            if ai_questions:
                return ai_questions
        except Exception:
            pass

    # Hardcoded fallback logic
    questions = []
    used_questions = set()
    
    # Target 15 questions total (2 marks each = 30 total)
    target_count = 15
    
    # Shuffle skills to provide variety
    random.shuffle(skills)
    
    # Cycle through skills multiple times to reach target_count
    skill_cycle = list(skills) * (target_count // max(len(skills), 1) + 1)
    random.shuffle(skill_cycle)
    
    for skill in skill_cycle:
        if len(questions) >= target_count:
            break
            
        skill_key = skill.strip()
        available = QUESTION_BANK.get(skill_key, [])
        
        if available:
            unused = [q for q in available if q["q"] not in used_questions]
            if unused:
                q_obj = random.choice(unused)
                used_questions.add(q_obj["q"])
                questions.append({
                    "skill": skill_key, 
                    "question": q_obj["q"],
                    "difficulty": q_obj["d"]
                })
                continue
        
        # Fallback to generic questions
        template_obj = random.choice(GENERIC_QUESTIONS)
        q_text = template_obj["q"].format(skill=skill_key)
        if q_text not in used_questions:
            used_questions.add(q_text)
            questions.append({
                "skill": skill_key, 
                "question": q_text,
                "difficulty": template_obj["d"]
            })
            
    # If we still need more questions, use all question bank skills
    if len(questions) < target_count:
        for extra_skill in ["Python", "JavaScript", "SQL", "React", "Java", "Docker"]:
            if len(questions) >= target_count: break
            available = QUESTION_BANK.get(extra_skill, [])
            unused = [q for q in available if q["q"] not in used_questions]
            for q_obj in unused:
                if len(questions) >= target_count: break
                used_questions.add(q_obj["q"])
                questions.append({
                    "skill": extra_skill, 
                    "question": q_obj["q"],
                    "difficulty": q_obj["d"]
                })

    return questions

from .eval_service import evaluate_technical_answer

def evaluate_answer(question, answer):
    """
    Evaluate a single quiz answer. Returns 0, 1, or 2 marks.
    2 marks = correct/strong answer
    1 mark  = partial answer
    0 marks = blank or very weak answer
    Each question carries 2 marks, 15 questions × 2 = 30 total.
    """
    if not answer or not answer.strip():
        return 0
    
    # Compute similarity-based score (0-100 scale)
    model_keywords = question.split()[-5:]
    model_answer_sim = f"The {question} involves {' '.join(model_keywords)}"
    
    raw_score = evaluate_technical_answer(answer, model_answer_sim)
    
    # Bonus for professional length/structure
    words = answer.split()
    if len(words) > 20: raw_score += 10
    if "." in answer: raw_score += 5
    
    raw_score = min(raw_score, 100)
    
    # Convert 0-100 raw score to 0-2 marks
    if raw_score >= 60:
        return 2  # Full marks
    elif raw_score >= 30:
        return 1  # Partial marks
    else:
        return 0  # No marks
