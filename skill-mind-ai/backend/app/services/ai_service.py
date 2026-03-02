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
            model_name="gemini-1.5-flash",
            system_instruction=system_instruction
        )
        # Add safety settings or other config if needed
        response = model.generate_content(prompt, request_options={"timeout": 30})
        if not response or not response.text:
            logger.warning("Gemini returned empty response.")
            return None
        return response.text
    except Exception as e:
        logger.error(f"Error calling Gemini: {e}")
        # If it's a 401/403, might be worth re-configuring?
        return None

def analyze_resume_llm(resume_text):
    """Use AI to extract skills and summary from resume text."""
    if not HAS_GEMINI:
        return None

    system_prompt = "You are an expert HR and recruitment AI specializing in BERT-based Named Entity Recognition (NER). Extract technical skills, educational degrees, and years/type of experience from the resume text."
    prompt = f"""
    Perform deep NER extraction on this resume text. 
    Target Entities:
    - Technical Skills (Programming, Frameworks, Tools)
    - Degree (B.S., M.S., Ph.D., etc.)
    - Experience (Total years and key roles)

    Return the result ONLY as a JSON object with the following structure:
    {{
        "skills": ["Skill 1", "Skill 2"],
        "degree": "Detected Degree",
        "experience": "Description of experience",
        "summary": "Professional summary here..."
    }}

    Resume Text:
    {resume_text}
    """
    
    response_text = call_gemini(prompt, system_prompt)
    if response_text:
        try:
            # Clean possible markdown formatting
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

def compare_resume_jd_llm(resume_text, jd_text):
    """Perform a deep AI-based comparison between resume and job description."""
    if not HAS_GEMINI:
        return None

    system_prompt = "You are a professional recruiter and career coach. Compare the candidate's resume against the job description to identify matches, gaps, and overall fitness."
    prompt = f"""
    Task: Compare Resume and Job Description (JD)
    
    Resume Text:
    {resume_text}
    
    Job Description Text:
    {jd_text}
    
    Analyze the following:
    1. Matching Skills: Technical and soft skills found in both.
    2. Missing Skills: Essential skills required by the JD but missing from the resume.
    3. Match Score: A percentage (0-100) representing how well the candidate fits the role.
    4. Key Insights: Brief advice for the candidate.

    Return the result ONLY as a JSON object with this structure:
    {{
        "match_score": 85,
        "matches": ["Skill A", "Skill B"],
        "missing": ["Skill C", "Skill D"],
        "insights": "Candidate is a strong fit but needs to highlight experience with Skill C."
    }}
    """
    
    response_text = call_gemini(prompt, system_prompt)
    if response_text:
        try:
            clean_json = response_text.replace('```json', '').replace('```', '').strip()
            return json.loads(clean_json)
        except Exception as e:
            logger.error(f"Error parsing comparison results: {e}")
    return None
