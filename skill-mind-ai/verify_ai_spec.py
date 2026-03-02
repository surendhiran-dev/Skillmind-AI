import sys
import os
import json

# Add backend to path
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.services.ai_service import analyze_resume_llm, generate_quiz_llm, HAS_GEMINI
from app.services.resume_service import analyze_resume
from app.services.interview_service import get_ai_response

def test_alignment():
    print(f"Gemini Active: {HAS_GEMINI}")
    if not HAS_GEMINI:
        print("Skipping LLM tests (Mock mode active)")
        return

    # 1. Test Resume Analysis (BERT/NER Alignment)
    resume_text = "John Doe. B.S. in Computer Science. 5 years experience in Python and React."
    print("\nTesting Resume Analysis (NER)...")
    analysis = analyze_resume(resume_text)
    print(json.dumps(analysis, indent=2))
    assert "degree" in analysis
    assert "experience" in analysis

    # 2. Test Quiz Generation (T5 Alignment)
    print("\nTesting Quiz Generation (T5)...")
    skills = ["Python", "Machine Learning"]
    quiz = generate_quiz_llm(skills)
    print(json.dumps(quiz, indent=2))
    assert isinstance(quiz, list)

    # 3. Test HR Interview (Instruction-Tuned Transformer)
    print("\nTesting HR Interview (Dynamic Follow-up)...")
    user_input = "I have led a team of 5 developers for two years."
    response = get_ai_response(user_input, "Leadership Experience", 1)
    print(json.dumps(response, indent=2))
    assert "response" in response
    assert "sentiment" in response

if __name__ == "__main__":
    test_alignment()
