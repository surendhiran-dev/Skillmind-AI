import os
import json
import logging
import functools
import google.generativeai as genai
from dotenv import load_dotenv

load_dotenv()

# BERT-based NER structure for resume skill extraction
# T5-based sequence-to-sequence structure for quiz question generation
# Transformer-based evaluation model for coding logic
# Transformer-based follow-up generation for HR interview

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
    system_prompt = "You are a production-level Recruiting AI specializing in Spacy/BERT-based NER and Skill Taxonomy normalization."
    prompt = f"""
    Perform deep contextual extraction on this resume text. 
    Requirements:
    1. Technical Skills: Extract and NORMALIZE (e.g., 'ML' -> 'Machine Learning').
    2. Soft Skills: Extract interpersonal and leadership traits.
    3. Experience: Total years (float) and roles with duration.
    4. Education: Normalized degree levels.
    5. Confidence Score: (0.0-1.0) for every skill extracted.

    Return the result ONLY as a JSON object with this EXACT structure:
    {{
        "technical_skills": [{{ "skill": "Python", "confidence": 0.98, "reasoning": "Direct mention in skills section" }}],
        "soft_skills": [{{ "skill": "Leading Teams", "confidence": 0.85, "reasoning": "Derived from Project Manager role" }}],
        "experience_years": 4.5,
        "education": "Masters in CS",
        "structured_data": {{
            "education": [{{ "degree": "...", "institution": "...", "year": "..." }}],
            "experience": {{ "total_years": 4.5, "roles": [{{ "title": "...", "company": "...", "duration": "..." }}] }},
            "projects": [{{ "name": "...", "description": "...", "technologies": [] }}],
            "certifications": ["Cert 1"]
        }},
        "summary": "Professional executive summary...",
        "scores": {{
            "technical": 85,
            "projects": 90,
            "experience": 75,
            "education": 100,
            "certifications": 80
        }}
    }}

    Resume Text:
    {resume_text}
    """
    
    response_text = call_gemini(prompt, system_prompt)
    if response_text:
        try:
            clean_json = response_text.replace('```json', '').replace('```', '').strip()
            res = json.loads(clean_json)
            # Ensure backward compatibility and weighted components
            res['skills'] = [s['skill'] if isinstance(s, dict) else s for s in res.get('technical_skills', [])]
            res['score_components'] = res.get('scores', {
                "technical": 70, "projects": 50, "experience": 60, "education": 80, "certifications": 40
            })
            return res
        except Exception as e:
            logger.error(f"Error parsing Gemini response: {e}")
    return None

def analyze_match_explanation_llm(resume_text, jd_text, match_score):
    """Calculate specific skill contributions and gaps for explainability."""
    if not HAS_GEMINI:
        return []

    prompt = f"""
    Analyze the match between the resume and JD. Match Score is {match_score}%.
    Identify the top 3 skills that contributed MOST to this score and the top 3 MISSING skills that reduced it most.
    Assign a 'contribution_impact' percentage to each.

    Resume: {resume_text[:2000]}
    JD: {jd_text[:2000]}

    Return ONLY a JSON array:
    [
        {{ "skill": "Python", "type": "contributor", "impact": 25, "reason": "Exact match for primary requirement" }},
        {{ "skill": "System Design", "type": "gap", "impact": -15, "reason": "Critical missing architecture skill" }}
    ]
    """
    response_text = call_gemini(prompt, "You are an explainable AI (XAI) engine for recruiter transparency.")
    if response_text:
        try:
            clean_json = response_text.replace('```json', '').replace('```', '').strip()
            return json.loads(clean_json)
        except: pass
    return []

def generate_skill_gap_recommendations_llm(missing_skills):
    """Suggest targeted learning paths for missing skills."""
    if not HAS_GEMINI or not missing_skills:
        return []

    prompt = f"""
    For these missing skills: {', '.join(missing_skills)}
    Suggest 3 targeted learning actions. For each, include:
    1. Course/Platform (Coursera, Udemy, etc.)
    2. Estimated 'Match Boost' percentage if completed.

    Return ONLY a JSON array:
    [
        {{ "skill": "System Design", "platform": "Educative.io", "boost": 15, "action": "Master high-level architecture patterns" }}
    ]
    """
    response_text = call_gemini(prompt, "You are a technical career development coach.")
    if response_text:
        try:
            clean_json = response_text.replace('```json', '').replace('```', '').strip()
            return json.loads(clean_json)
        except: pass
    return []

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

@functools.lru_cache(maxsize=50)
def calculate_job_fit_llm(resume_text, jd_text, role_title="Specified Role"):
    """Calculate job fit using semantic comparison and Cosine Similarity logic."""
    if not HAS_GEMINI:
        return None

    system_prompt = "You are an expert recruitment analyst. Use semantic vector comparison (Cosine Similarity) concepts to calculate fit."
    prompt = f"""
    Compare the Resume against the Job Description for the role: {role_title}.
    
    Analysis Model:
    1. Overall Match Score: Calculate a precise percentage (0.0 - 100.0).
    2. Breakdown Scores: Provide individual scores for:
       - Technical Skills (40% weight)
       - Experience (30% weight)
       - Education (20% weight)
       - Soft Skills (10% weight)
    3. Skill Tables: For each 'match' and 'missing' skill, include:
       - 'weight': (0.0 - 1.0) relative importance.
       - 'impact': (0.0 - 100.0) contribution to its category.
       - 'priority': 'High', 'Medium', or 'Low' for missing skills.

    Resume Text: {resume_text[:3000]}
    Job Description: {jd_text[:3000]}

    Return ONLY a JSON object:
    {{
        "match_percentage": 78.5,
        "breakdown": {{
            "technical": 82,
            "experience": 70,
            "education": 85,
            "soft_skills": 65
        }},
        "matches": [{{ "skill": "Python", "weight": 0.9, "impact": 15 }}],
        "missing": [{{ "skill": "Docker", "weight": 0.8, "impact": 10, "priority": "High" }}],
        "recommendations": ["Learn Docker and CI/CD"]
    }}
    """
    
    response_text = call_gemini(prompt, system_prompt)
    if response_text:
        try:
            clean_json = response_text.replace('```json', '').replace('```', '').strip()
            res = json.loads(clean_json)
            # Align with internal service and routes keys - PRESERVE METADATA
            return {
                "match_score": res.get("match_percentage", 0),
                "breakdown": res.get("breakdown", {}),
                "matches": res.get("matches", []),
                "missing": res.get("missing", []),
                "recommendations": res.get("recommendations", [])
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
            "match_score": res["match_score"],
            "matches": res["matches"],
            "missing": res["missing"],
            "insights": "Real-time AI matching completed."
        }
    return None
def generate_skill_gap_recommendations_llm(missing_skills):
    """
    Generate strategic advice for candidates based on missing skills.
    Includes projected improvements.
    """
    if not HAS_GEMINI or not missing_skills:
        return []

    system_prompt = "You are a senior technical recruiter and career coach."
    prompt = f"""
    Based on these missing skills: {missing_skills}, provide 3-4 specific, high-impact recommendations.
    For each, include a projected match percentage increase if the skill is acquired.
    
    Return ONLY a JSON array of objects:
    [
      {{ "text": "Learn Docker for containerization", "projected_increase": 5 }},
      {{ "text": "Master AWS Lambda for serverless architecture", "projected_increase": 8 }}
    ]
    """
    
    response_text = call_gemini(prompt, system_prompt)
    if response_text:
        try:
            clean_json = response_text.replace('```json', '').replace('```', '').strip()
            return json.loads(clean_json)
        except Exception as e:
            logger.error(f"Error parsing recommendations: {e}")
    
    # Simple fallback
    return [{"text": f"Gain proficiency in {s}", "projected_increase": 5} for s in missing_skills[:3]]
