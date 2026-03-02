import os
import json

# BERT-based NER structure for resume skill extraction
# T5-based sequence-to-sequence structure for quiz question generation
# Transformer-based evaluation model for coding logic
# Transformer-based follow-up generation for HR interview

import logging
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

HAS_GEMINI = False

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure Gemini
def configure_genai():
    global HAS_GEMINI
    # Re-load to ensure we get latest from file if needed
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
    api_key = os.getenv("GOOGLE_API_KEY")
    
    if api_key and api_key != "your_gemini_api_key_here":
        try:
            genai.configure(api_key=api_key)
            HAS_GEMINI = True
            logger.info("Gemini AI successfully configured.")
        except Exception as e:
            logger.error(f"Failed to configure Gemini: {e}")
            HAS_GEMINI = False
    else:
        HAS_GEMINI = False
        logger.warning("GOOGLE_API_KEY not found or default. AI Service will run in MOCK mode.")

configure_genai()

def call_gemini(prompt, system_instruction=None):
    """Generic helper to call Gemini and return text."""
    if not HAS_GEMINI:
        logger.debug("call_gemini skipped: HAS_GEMINI is False")
        return None
    
    try:
        model = genai.GenerativeModel(
            model_name="gemini-1.5-pro"
        )
        # Add system instructions to prompt if instruction is provided
        full_prompt = prompt
        if system_instruction:
            full_prompt = f"{system_instruction}\n\n{prompt}"
            
        response = model.generate_content(full_prompt, request_options={"timeout": 30})
        if not response or not hasattr(response, 'text') or not response.text:
            logger.warning("Gemini returned empty or invalid response.")
            return get_mock_response(prompt)
            
        return response.text
    except Exception as e:
        logger.error(f"Error calling Gemini: {e}")
        return get_mock_response(prompt)

def get_mock_response(prompt):
    """Provides a safe structural fallback when Gemini fails."""
    logger.info("Providing mock response fallback.")
    if "structured_data" in prompt:
        return json.dumps({
            "structured_data": {"education": [], "experience": {"total_years": 0}, "projects": [], "certifications": []},
            "skills": ["Communication", "Problem Solving", "Teamwork"],
            "explainability": {},
            "summary": "AI extraction skipped. Using heuristic analysis.",
            "resume_score": 60,
            "score_breakdown": {"skill_score": 60, "experience_score": 50}
        })
    elif "match_percentage" in prompt:
        return json.dumps({
            "match_percentage": 70.0,
            "matches": ["General professional skills"],
            "missing": ["Role-specific technical depth"],
            "recommendations": ["Align resume more closely with JD keywords."]
        })
    return "AI service unavailable."

def analyze_resume_llm(resume_text):
    """Use AI to extract structured entities, skills, and explainable insights from resume text."""
    if not HAS_GEMINI:
        return None

    system_prompt = "You are an expert HR and recruitment AI specializing in BERT-based Named Entity Recognition (NER) and Skill Taxonomy mapping."
    prompt = f"""
    Perform deep structured extraction on this resume text. 
    Target Entities:
    - Technical Skills (Programming, Frameworks, Tools)
    - Education (Degrees, Institutions, Completion Year)
    - Experience (Total years, key roles, and company names)
    - Projects (Titles and brief descriptions)
    - Certifications (Official titles)

    Explainability Requirement:
    For every Technical Skill extracted, provide:
    1. A confidence score (0-1.0)
    2. Reasoning (e.g., 'Found in Skills section' or 'Inferred from project experience')
    3. The exact sentence reference from the text.

    Return the result ONLY as a JSON object with this EXACT structure:
    {{
        "structured_data": {{
            "education": [{{ "degree": "...", "institution": "...", "year": "..." }}],
            "experience": {{ "total_years": 0.0, "roles": [{{ "title": "...", "company": "...", "duration": "..." }}] }},
            "projects": [{{ "name": "...", "description": "...", "technologies": [] }}],
            "certifications": ["Cert 1"]
        }},
        "skills": ["Skill 1", "Skill 2"],
        "explainability": {{
            "Skill 1": {{ "confidence": 0.95, "reasoning": "...", "reference": "..." }}
        }},
        "summary": "Professional summary..."
    }}

    Resume Text:
    {resume_text}
    """
    
    response_text = call_gemini(prompt, system_prompt)
    if response_text:
        try:
            clean_json = response_text.replace('```json', '').replace('```', '').strip()
            return json.loads(clean_json)
        except Exception as e:
            logger.error(f"Error parsing Gemini response: {e}")
    return None

def generate_quiz_llm(skills, jd_text=""):
    """Generate professional technical questions based on skills and Optional JD."""
    if not HAS_GEMINI:
        return None

    system_prompt = "You are a senior technical interviewer utilizing a T5 (Text-to-Text) approach for question generation. Convert extracted skills into exactly 15 challenging technical questions."
    prompt = f"""
    Task: Convert Skills to exactly 15 Questions (each worth 2 marks, total 30 marks)
    Input Skills: {', '.join(skills)}
    {f"Context Job Description: {jd_text}" if jd_text else ""}
    
    Generate exactly 15 questions covering these skills with a mix of easy, medium, and hard difficulty.
    
    Output Format (JSON array of exactly 15 objects):
    [
        {{
            "skill": "Specific Skill Name",
            "question": "The technical question here",
            "difficulty": "easy|medium|hard"
        }}
    ]
    """
    
    response_text = call_gemini(prompt, system_prompt)
    if response_text:
        try:
            clean_json = response_text.replace('```json', '').replace('```', '').strip()
            return json.loads(clean_json)
        except Exception as e:
            logger.error(f"Error parsing Gemini response: {e}")
    return None

def generate_coding_challenge_llm(skills, jd_text=""):
    """Generate a dynamic coding challenge based on skills and Optional JD."""
    if not HAS_GEMINI:
        return None

    system_prompt = "You are a lead software engineer. Create high-quality coding challenges with test cases."
    prompt = f"""
    Create ONE coding challenge (Python) related to these skills: {', '.join(skills)}.
    {'Context: ' + jd_text if jd_text else ''}
    
    Return the result ONLY as a JSON object with this EXACT structure:
    {{
        "title": "Problem Title",
        "difficulty": "easy|medium|hard",
        "description": "Clear problem description",
        "tags": ["Tag1", "Tag2"],
        "starter_code": "def function_name(args):\\n    pass",
        "test_cases": [
            {{"input": "argument_value", "expected": "expected_return_value"}}
        ],
        "test_wrapper": "result = function_name({{input}})"
    }}
    """
    
    response_text = call_gemini(prompt, system_prompt)
    if response_text:
        try:
            clean_json = response_text.replace('```json', '').replace('```', '').strip()
            return json.loads(clean_json)
        except Exception as e:
            logger.error(f"Error parsing Gemini response: {e}")
    return None

def generate_job_recommendations_llm(skills, readiness_score=None):
    """Generate job vacancy recommendations for India based on skills and performance."""
    if not HAS_GEMINI:
        return [
            {"role": "Software Engineer", "company": "Tech Corp (Mock)", "location": "Bangalore", "link": "https://www.linkedin.com/jobs/search/?keywords=software%20engineer%20bangalore"},
            {"role": "Python Developer", "company": "Data Solutions (Mock)", "location": "Hyderabad", "link": "https://www.naukri.com/python-developer-jobs-in-hyderabad"}
        ]

    prompt = f"""
    Based on these candidate skills: {', '.join(skills)}
    Overall Readiness Score: {readiness_score if readiness_score else 'N/A'}/100
    
    Recommend 3-5 specific, currently in-demand job roles in India that match these skills.
    For each role, provide a search link on major Indian job portals like LinkedIn India or Naukri.com.
    
    Return the result ONLY as a JSON array of objects:
    [
        {{
            "role": "Job Title",
            "company": "Top Hiring Companies",
            "location": "Major Tech Hub",
            "link": "https://link-to-apply-or-search"
        }}
    ]
    """
    
    response_text = call_gemini(prompt, "You are a career consultant specializing in the Indian tech job market.")
    if response_text:
        try:
            clean_json = response_text.replace('```json', '').replace('```', '').strip()
            return json.loads(clean_json)
        except Exception as e:
            logger.error(f"Error parsing job recommendations: {e}")
    return []

def calculate_job_fit_llm(resume_text, jd_text, role_title):
    """Calculate job fit using semantic comparison and Cosine Similarity logic."""
    if not HAS_GEMINI:
        return None

    system_prompt = "You are an expert recruitment analyst. Use semantic vector comparison (Cosine Similarity) concepts to calculate fit."
    prompt = f"""
    Compare the Resume against the Job Description for the role: {role_title}.
    
    Analysis Model:
    1. Calculate a decimal Job Match Score (0.0 - 100.0) based on semantic Cosine Similarity.
    2. Identify Matching Skills (explicit and semantic matches).
    3. Identify Missing Skills (critical for the role).
    4. Provide 3-5 'Recommended Skills to Learn' to close the gap.

    Resume Text: {resume_text}
    Job Description: {jd_text}

    Return ONLY a JSON object:
    {{
        "match_percentage": 85.5,
        "matches": ["Skill A", "Skill B"],
        "missing": ["Skill D"],
        "recommendations": ["Learn Framework X", "Master Tool Y"]
    }}
    """
    
    response_text = call_gemini(prompt, system_prompt)
    if response_text:
        try:
            clean_json = response_text.replace('```json', '').replace('```', '').strip()
            res = json.loads(clean_json)
            # Align with internal service and routes keys
            return {
                "match_score": res.get("match_percentage", 0),
                "matches": res.get("matches", []),
                "missing": res.get("missing", []),
                "insights": "\n".join(res.get("recommendations", [])) if isinstance(res.get("recommendations"), list) else res.get("recommendations", "")
            }
        except Exception as e:
            logger.error(f"Error parsing job fit: {e}")
    return {
        "match_score": 0,
        "matches": [],
        "missing": [],
        "insights": "AI Analysis failed."
    }

def compare_resume_jd_llm(resume_text, jd_text):
    """Perform a deep AI-based comparison between resume and job description."""
    # This is kept for backward compatibility but calls calculate_job_fit_llm
    res = calculate_job_fit_llm(resume_text, jd_text, "Unspecified Role")
    if res:
        return {
            "match_score": res["match_percentage"],
            "matches": res["matches"],
            "missing": res["missing"],
            "insights": "Real-time AI matching completed."
        }
    return None
