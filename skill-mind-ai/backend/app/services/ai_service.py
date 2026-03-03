import os
import re
import json
import logging
import functools
from openai import OpenAI
from dotenv import load_dotenv

load_dotenv()

HAS_OPENROUTER = False
HAS_AI = False
client = None
DEFAULT_MODEL = "openai/gpt-3.5-turbo"

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configure AI Providers
def configure_ai():
    global HAS_OPENROUTER, HAS_AI, client, DEFAULT_MODEL
    # Re-load to ensure we get latest from file if needed
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
    
    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key and openai_key.startswith("sk-or-v1"):
        try:
            client = OpenAI(
                base_url="https://openrouter.ai/api/v1",
                api_key=openai_key,
            )
            HAS_OPENROUTER = True
            HAS_AI = True
            logger.info("OpenRouter AI successfully configured.")
        except Exception as e:
            logger.error(f"Failed to configure OpenRouter: {e}")
            
    if not HAS_AI:
        logger.warning("No OpenRouter API key configured. AI Service will run in LOCAL/MOCK mode.")

configure_ai()

def call_ai(prompt, system_instruction=None):
    """Call OpenRouter and return text."""
    if not HAS_OPENROUTER:
        logger.debug("call_ai skipped: OpenRouter not configured")
        return None
    
    try:
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        messages.append({"role": "user", "content": prompt})
        
        completion = client.chat.completions.create(
            extra_headers={
                "HTTP-Referer": "http://localhost:5000",
                "X-OpenRouter-Title": "SkillMind AI",
            },
            model=DEFAULT_MODEL,
            messages=messages,
        )
        return completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Error calling OpenRouter: {e}")
        return None

# Comprehensive Local Skill Library for Fallback Extraction
SKILL_LIBRARY = {
    "Technical": [
        "Python", "Java", "JavaScript", "C++", "C#", "SQL", "NoSQL", "React", "Angular", "Vue", "Node.js", 
        "AWS", "Azure", "GCP", "Docker", "Kubernetes", "CI/CD", "Git", "Machine Learning", "Deep Learning",
        "TensorFlow", "PyTorch", "Pandas", "NumPy", "Scikit-Learn", "FastAPI", "Flask", "Django", "MongoDB",
        "PostgreSQL", "Redis", "Elasticsearch", "Spark", "Hadoop", "Tableau", "PowerBI", "R", "Go", "Rust",
        "TypeScript", "HTML", "CSS", "Sass", "Tailwind", "REST API", "GraphQL"
    ],
    "Soft": [
        "Communication", "Leadership", "Teamwork", "Problem Solving", "Critical Thinking", "Adaptability",
        "Time Management", "Emotional Intelligence", "Public Speaking", "Writing", "Project Management", "Agile"
    ],
    "Experience": [
        "Senior", "Lead", "Architect", "Manager", "Developer", "Engineer", "Analyst", "Intern", "Junior", "Associate"
    ]
}

def local_extract_skills(text):
    """Fallback skill extraction using keyword matching."""
    if not text: return {"Technical": [], "Soft": []}
    text_lower = text.lower()
    found = {"Technical": [], "Soft": []}
    
    for category in ["Technical", "Soft"]:
        for skill in SKILL_LIBRARY[category]:
            # Regex for better matching:
            # If skill has special chars (e.g. C++, C#), don't use \b boundaries on both sides
            if any(c in skill for c in "+#.-"):
                pattern = re.escape(skill.lower())
            else:
                pattern = r'\b' + re.escape(skill.lower()) + r'\b'
                
            import re
            if re.search(pattern, text_lower):
                found[category].append({"skill": skill, "confidence": 0.7})
    return found

def local_calculate_job_fit(resume_text, jd_text):
    """Fallback matching logic using local extraction."""
    logger.info(f"DEBUG: Local Fit. Resume Len: {len(resume_text)}, JD Len: {len(jd_text)}")
    
    res_skills = local_extract_skills(resume_text)
    jd_skills = local_extract_skills(jd_text)
    
    # Debug logging as previously implemented
    print(f"DEBUG: Extracted Resume Skills: {res_skills}")
    print(f"DEBUG: Extracted JD Skills: {jd_skills}")
    
    res_tech = {s['skill'].lower() for s in res_skills['Technical']}
    jd_tech = {s['skill'].lower() for s in jd_skills['Technical']}
    
    matching = [s for s in jd_skills['Technical'] if s['skill'].lower() in res_tech]
    missing = [s for s in jd_skills['Technical'] if s['skill'].lower() not in res_tech]
    
    if not jd_skills['Technical']:
        # Improved fallback for short JDs (3-tier matching)
        resume_lower = resume_text.lower()
        jd_lower = jd_text.strip().lower()
        
        # Step 1: Try exact phrase match
        if jd_lower and jd_lower in resume_lower:
            match_score = min(65, 50 + len(jd_lower))
            insights = f"Local Analysis: Exact phrase '{jd_text.strip()}' found in resume."
        else:
            # Step 2: Try bigrams
            jd_words = [w.strip().lower() for w in jd_text.split() if len(w.strip()) > 2]
            bigrams = [f"{jd_words[i]} {jd_words[i+1]}" for i in range(len(jd_words) - 1)]
            found_bigrams = [bg for bg in bigrams if bg in resume_lower]
            
            # Step 3: Individual words
            found_words = [w for w in jd_words if w in resume_lower]
            
            if found_bigrams:
                match_score = min(60, (len(found_bigrams) / max(len(bigrams), 1)) * 100 + 15)
                insights = f"Local Analysis: Found matching phrases: {', '.join(found_bigrams[:5])}."
            elif found_words:
                match_score = min(55, (len(found_words) / len(jd_words)) * 100) if jd_words else 20
                insights = f"Local Analysis: Found matching terms: {', '.join(found_words[:5])}."
            else:
                match_score = 10
                insights = "Local Analysis: No direct matches found."
    else:
        match_score = (len(matching) / len(jd_skills['Technical']) * 100)
        insights = "Local Analysis: Results based on keyword similarity indexing."

    print(f"DEBUG: Raw Similarity Score: {match_score}")

    return {
        "match_score": round(match_score, 1),
        "matching_skills": [s['skill'] for s in matching],
        "missing_skills": [s['skill'] for s in missing],
        "breakdown": {
            "technical": round(match_score, 1),
            "experience": 50 if any(k.lower() in resume_text.lower() for k in ["Senior", "Lead", "Architect", "Manager", "Years"]) else 30,
            "education": 70 if any(k.lower() in resume_text.lower() for k in ["Degree", "Bachelor", "B.E", "B.Tech", "Master"]) else 40,
            "soft_skills": 60 if res_skills['Soft'] else 40
        },
        "insights": insights,
        "method": "Local Keyword Extraction"
    }

# Removed call_gemini

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
    
    response_text = call_ai(prompt, system_prompt)
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
    if not HAS_AI:
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
    response_text = call_ai(prompt, "You are an explainable AI (XAI) engine for recruiter transparency.")
    if response_text:
        try:
            clean_json = response_text.replace('```json', '').replace('```', '').strip()
            return json.loads(clean_json)
        except: pass
    return []

def generate_skill_gap_recommendations_llm(missing_skills):
    """Suggest targeted learning paths for missing skills."""
    if not HAS_AI or not missing_skills:
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
    response_text = call_ai(prompt, "You are a technical career development coach.")
    if response_text:
        try:
            clean_json = response_text.replace('```json', '').replace('```', '').strip()
            return json.loads(clean_json)
        except: pass
    return []

def generate_quiz_llm(skills, jd_text=""):
    """Generate professional technical questions based on skills and Optional JD."""
    if not HAS_AI:
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
    
    response_text = call_ai(prompt, system_prompt)
    if response_text:
        try:
            clean_json = response_text.replace('```json', '').replace('```', '').strip()
            return json.loads(clean_json)
        except Exception as e:
            logger.error(f"Error parsing Gemini response: {e}")
    return None

def generate_coding_challenge_llm(skills, jd_text=""):
    """Generate a dynamic coding challenge based on skills and Optional JD."""
    if not HAS_AI:
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
    
    response_text = call_ai(prompt, system_prompt)
    if response_text:
        try:
            clean_json = response_text.replace('```json', '').replace('```', '').strip()
            return json.loads(clean_json)
        except Exception as e:
            logger.error(f"Error parsing Gemini response: {e}")
    return None

def generate_job_recommendations_llm(skills, readiness_score=None):
    """Generate job vacancy recommendations for India based on skills and performance."""
    if not HAS_AI:
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
    
    response_text = call_ai(prompt, "You are a career consultant specializing in the Indian tech job market.")
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
    if not HAS_AI:
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
    
    response_text = call_ai(prompt, system_prompt)
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
            
    return local_calculate_job_fit(resume_text, jd_text)

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
    if not HAS_AI or not missing_skills:
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
    
    response_text = call_ai(prompt, system_prompt)
    if response_text:
        try:
            clean_json = response_text.replace('```json', '').replace('```', '').strip()
            return json.loads(clean_json)
        except Exception as e:
            logger.error(f"Error parsing recommendations: {e}")
    
    # Simple fallback
    return [{"text": f"Gain proficiency in {s}", "projected_increase": 5} for s in missing_skills[:3]]
