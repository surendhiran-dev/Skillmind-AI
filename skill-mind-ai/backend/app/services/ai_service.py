import os
import re
import json
import logging
import functools
import random
from openai import OpenAI
import anthropic
from dotenv import load_dotenv

load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# AI Module Configurations
MODULE_CONFIGS = {
    'resume': {'client': None, 'anthropic_client': None, 'has_ai': False, 'has_anthropic': False, 'has_or': False, 'model': "openai/gpt-oss-20b"},
    'quiz': {'client': None, 'anthropic_client': None, 'has_ai': False, 'has_anthropic': False, 'has_or': False, 'model': "openai/gpt-oss-20b"},
    'coding': {'client': None, 'anthropic_client': None, 'has_ai': False, 'has_anthropic': False, 'has_or': False, 'model': "openai/gpt-oss-20b"},
    'interview': {'client': None, 'anthropic_client': None, 'has_ai': False, 'has_anthropic': False, 'has_or': False, 'model': "openai/gpt-oss-20b"},
    'support': {'client': None, 'anthropic_client': None, 'has_ai': False, 'has_anthropic': False, 'has_or': False, 'model': "openai/gpt-oss-20b"},
    'default': {'client': None, 'anthropic_client': None, 'has_ai': False, 'has_anthropic': False, 'has_or': False, 'model': "openai/gpt-oss-20b"}
}

DEFAULT_MODEL = "openai/gpt-oss-20b"
HAS_AI = False # Global flag for any AI availability

def initialize_client(api_key):
    """Helper to create an OpenAI client from a key (OpenRouter, NVIDIA NIM, or Standard)."""
    if not api_key: return None, False, False
    
    # NVIDIA NIM Support
    if api_key.startswith("nvapi-"):
        try:
            client = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=api_key)
            return client, True, False # Not OpenRouter
        except Exception as e:
            logger.error(f"NVIDIA NIM init failed: {e}")

    # OpenRouter Support
    if api_key.startswith("sk-or-v1"):
        try:
            client = OpenAI(base_url="https://openrouter.ai/api/v1", api_key=api_key)
            return client, True, True
        except Exception as e:
            logger.error(f"OpenRouter init failed: {e}")
            
    # Standard OpenAI Support
    elif api_key.startswith("sk-"):
        try:
            return OpenAI(api_key=api_key), True, False
        except Exception as e:
            logger.error(f"Standard OpenAI init failed: {e}")
    return None, False, False

def configure_ai():
    global HAS_AI
    load_dotenv(os.path.join(os.path.dirname(__file__), '..', '..', '.env'))
    
    # 1. Initialize Module Specific Keys
    key_mapping = {
        'resume': 'RESUME_AI_KEY',
        'quiz': 'QUIZ_AI_KEY',
        'coding': 'CODING_AI_KEY',
        'interview': 'INTERVIEW_AI_KEY',
        'support': 'SUPPORT_AI_KEY',
        'default': 'OPENAI_API_KEY'
    }
    
    anthropic_key = os.getenv('ANTHROPIC_API_KEY')
    anthropic_client = None
    if anthropic_key:
        try:
            anthropic_client = anthropic.Anthropic(api_key=anthropic_key)
            logger.info("Anthropic client initialized.")
        except Exception as e:
            logger.error(f"Anthropic init failed: {e}")

    for mod, env_var in key_mapping.items():
        key = os.getenv(env_var)
        client, has_ai, has_or = initialize_client(key)
        
        # Fallback to default if module key is missing
        if not client and mod != 'default':
            default_key = os.getenv('OPENAI_API_KEY')
            client, has_ai, has_or = initialize_client(default_key)
            
        MODULE_CONFIGS[mod]['client'] = client
        MODULE_CONFIGS[mod]['has_ai'] = has_ai
        MODULE_CONFIGS[mod]['has_or'] = has_or
        
        # Add Anthropic support
        if anthropic_client:
            MODULE_CONFIGS[mod]['anthropic_client'] = anthropic_client
            MODULE_CONFIGS[mod]['has_anthropic'] = True
            HAS_AI = True

        if has_ai: HAS_AI = True
        
    logger.info(f"AI configurations initialized. Overall AI: {HAS_AI}")

configure_ai()

def clean_json_response(response_text):
    """Helper to extract and clean JSON from AI responses (handles {} and [])."""
    if not response_text:
        return None
    try:
        # 1. Basic markdown cleaning
        clean_text = re.sub(r'```json\s*|\s*```', '', response_text).strip()
        
        # 2. Find outermost structure (Object or Array)
        first_brace = clean_text.find('{')
        first_bracket = clean_text.find('[')
        
        # Determine the start and end of the outermost JSON structure
        start_idx = -1
        end_char = ''
        
        if first_brace != -1 and (first_bracket == -1 or first_brace < first_bracket):
            start_idx = first_brace
            end_char = '}'
        elif first_bracket != -1:
            start_idx = first_bracket
            end_char = ']'
            
        if start_idx != -1:
            last_idx = clean_text.rfind(end_char)
            if last_idx != -1:
                clean_text = clean_text[start_idx:last_idx+1]
        
        return json.loads(clean_text)
    except Exception as e:
        logger.error(f"JSON parsing error: {e}. Raw: {response_text[:100]}...")
        return None

def call_ai(prompt, system_instruction=None, module='default', history=None):
    """
    General purpose AI call for OpenAI/OpenRouter systems.
    Supports optional conversation history for more dynamic interactions.
    """
    config = MODULE_CONFIGS.get(module, MODULE_CONFIGS['default'])
    
    # Special handling for HR Interview module - prioritize Anthropic
    if module == 'interview' and config.get('has_anthropic'):
        return call_anthropic(prompt, system_instruction)

    if not config['has_ai']:
        # Fallback to Anthropic if OpenAI is missing but Anthropic is available
        if config.get('has_anthropic'):
            return call_anthropic(prompt, system_instruction)
        logger.debug(f"call_ai skipped for {module}: No client configured")
        return None
    
    try:
        messages = []
        if system_instruction:
            messages.append({"role": "system", "content": system_instruction})
        
        # Add conversation history if provided
        if history:
            messages.extend(history)
            
        messages.append({"role": "user", "content": prompt})
        
        # Use config model, but handle OpenRouter specific prefixes if needed
        model = config.get('model', DEFAULT_MODEL)
        if config['has_or'] and not any(p in model for p in ['/', 'openai/', 'anthropic/', 'google/']):
            # If it's OpenRouter and model has no provider prefix, and it's a standard model, 
            # maybe it needs one. But usually config['model'] should be correct.
            pass

        args = {
            "model": model,
            "messages": messages,
        }
        
        if config['has_or']:
            # OpenRouter headers are optional but recommended. 
            # Removing them for now to ensure absolute minimum configuration for stability.
            pass
        
        logger.info(f"Calling AI for {module} using model {model} (OR: {config['has_or']})")
        completion = config['client'].chat.completions.create(**args)
        
        if not completion.choices:
            logger.error(f"Empty AI response for {module}")
            return None
            
        return completion.choices[0].message.content
    except Exception as e:
        logger.error(f"Error calling {module} AI: {str(e)}")
        # Log the full exception details for debugging
        import traceback
        logger.error(traceback.format_exc())
        return None

def call_anthropic(prompt, system_instruction=None):
    """Call the Anthropic API (Claude 3.5 Sonnet)."""
    try:
        # Get the global anthropic client from MODULE_CONFIGS['default']
        client = MODULE_CONFIGS['default']['anthropic_client']
        if not client: return None

        message = client.messages.create(
            model="claude-3-5-sonnet-20240620",
            max_tokens=2048,
            system=system_instruction if system_instruction else "You are a professional AI HR Interviewer.",
            messages=[
                {"role": "user", "content": prompt}
            ]
        )
        return message.content[0].text
    except Exception as e:
        logger.error(f"Error calling Anthropic AI: {e}")
        return None

# Comprehensive Local Skill Library for Fallback Extraction
SKILL_LIBRARY = {
    "Technical": [
        "Python", "Java", "JavaScript", "C++", "C#", "SQL", "NoSQL", "React", "Angular", "Vue", "Node.js", 
        "AWS", "Azure", "GCP", "Docker", "Kubernetes", "CI/CD", "Git", "Machine Learning", "Deep Learning",
        "TensorFlow", "PyTorch", "Pandas", "NumPy", "Scikit-Learn", "FastAPI", "Flask", "Django", "MongoDB",
        "PostgreSQL", "Redis", "Elasticsearch", "Spark", "Hadoop", "Tableau", "PowerBI", "R", "Go", "Rust",
        "TypeScript", "HTML", "CSS", "Sass", "Tailwind", "REST API", "GraphQL", "Agile", "Scrum", "Mentoring",
        "Unit Testing", "TDD", "Microservices", "Serverless", "System Design", "API Development"
    ],
    "Soft": [
        "Communication", "Leadership", "Teamwork", "Problem Solving", "Critical Thinking", "Adaptability",
        "Time Management", "Emotional Intelligence", "Public Speaking", "Writing", "Project Management", "Agile",
        "Collaboration", "Presentation", "Mentoring", "Strategic Planning", "Adaptable", "Good Team Player"
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
            matching = [{"skill": jd_text.strip(), "confidence": 0.8}]
        else:
            # Step 2: Try bigrams
            jd_words = [w.strip().lower() for w in jd_text.split() if len(w.strip()) > 2]
            # Simple stop words filter
            stop_words = {'and', 'the', 'for', 'with', 'who', 'has', 'great', 'this', 'that'}
            jd_words = [w for w in jd_words if w not in stop_words]
            
            bigrams = [f"{jd_words[i]} {jd_words[i+1]}" for i in range(len(jd_words) - 1)]
            found_bigrams = [bg for bg in bigrams if bg in resume_lower]
            
            # Step 3: Individual words
            found_words = [w for w in jd_words if w in resume_lower]
            missing_words = [w for w in jd_words if w not in found_words]
            
            if found_bigrams:
                match_score = min(60, (len(found_bigrams) / max(len(bigrams), 1)) * 100 + 15)
                insights = f"Local Analysis: Found matching phrases: {', '.join(found_bigrams[:5])}."
                matching = [{"skill": bg, "confidence": 0.75} for bg in found_bigrams]
                missing = [{"skill": bg, "confidence": 0.3} for bg in bigrams if bg not in found_bigrams]
            elif found_words:
                match_score = min(55, (len(found_words) / len(jd_words)) * 100) if jd_words else 20
                insights = f"Local Analysis: Found matching terms: {', '.join(found_words[:5])}."
                matching = [{"skill": w, "confidence": 0.7} for w in found_words]
                missing = [{"skill": w, "confidence": 0.2} for w in missing_words]
            else:
                match_score = 10
                insights = "Local Analysis: No direct matches found."
                missing = [{"skill": w, "confidence": 0.1} for w in jd_words]
    else:
        match_score = (len(matching) / len(jd_skills['Technical']) * 100)
        insights = "Local Analysis: Results based on keyword similarity indexing."

    print(f"DEBUG: Raw Similarity Score: {match_score}")

    return {
        "match_score": round(match_score, 1),
        "matching_skills": [s['skill'] for s in matching],
        "missing_skills": [s['skill'] for s in missing],
        "partial_skills": [],
        "breakdown": {
            "technical": round(match_score, 1),
            "experience": 50 if any(k.lower() in resume_text.lower() for k in ["Senior", "Lead", "Architect", "Manager", "Years"]) else 30,
            "projects": 40 if any(k.lower() in resume_text.lower() for k in ["Project", "GitHub", "Vercel", "Developed", "Built"]) else 20,
            "education": 70 if any(k.lower() in resume_text.lower() for k in ["Degree", "Bachelor", "B.E", "B.Tech", "Master"]) else 40,
            "certifications": 50 if any(k.lower() in resume_text.lower() for k in ["Certified", "Certification", "Certificate", "AWS-", "Google-"]) else 10
        },
        "insights": insights,
        "method": "Local Semantic Heuristics"
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
    
    response_text = call_ai(prompt, system_prompt, module='resume')
    res = clean_json_response(response_text)
    if res:
        # Ensure backward compatibility and weighted components
        res['skills'] = [s['skill'] if isinstance(s, dict) else s for s in res.get('technical_skills', [])]
        res['score_components'] = res.get('scores', {
            "technical": 70, "projects": 50, "experience": 60, "education": 80, "certifications": 40
        })
        return res
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
    response_text = call_ai(prompt, "You are an explainable AI (XAI) engine for recruiter transparency.", module='resume')
    return clean_json_response(response_text) or []

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
    response_text = call_ai(prompt, "You are a technical career development coach.", module='resume')
    return clean_json_response(response_text) or []

def generate_quiz_llm(skills, jd_text=""):
    """Generate professional technical questions based on skills and Optional JD."""
    if not HAS_AI:
        return None

    seed = random.randint(1, 1000000)
    system_prompt = f"You are a sophisticated Technical Assessment Engine. Your goal is to generate 30 high-fidelity, UNIQUE, and skill-diverse MCQs. [Session ID: {seed}]"
    prompt = f"""
    Task: Create exactly 30 UNIQUE and HIGH-QUALITY MCQs based on the following candidate profile.
    
    Target Skills: {', '.join(skills)}
    {f"Context Job Description: {jd_text}" if jd_text else ""}
    
    CRITICAL REQUIREMENTS for Uniqueness & Coverage:
    1. SKILL COVERAGE: You MUST distribute questions across ALL target skills. Aim for 2-3 questions per major skill. Do not neglect any listed skill.
    2. ZERO REPETITION: Every question must be fundamentally different. Do not repeat the same concept (e.g., if you ask about 'React Hooks' once, don't ask about another hook unless it's a completely different scenario).
    3. NO BASIC QUESTIONS: Avoid 'What is...' or 'Which is a feature of...' questions. Focus on:
       - Real-world Scenarios (e.g., 'You are debugging a memory leak in X...')
       - Edge Cases (e.g., 'How does X behave when Y is null but Z is active?')
       - Performance Trade-offs (e.g., 'Why choose approach A over B?')
    4. DIVERSE QUESTION TYPES: Rotate through these types for each skill:
       - Architectural/System Design
       - Debugging/Troubleshooting
       - Best Practices/Security
       - Advanced Implementation
    5. CONCEPT DIVERSITY: Avoid 'Small Changes' between questions. Each question must require a distinct mental model to solve.
    6. OPTIONS: Each question must have 4 distinct, plausible, and high-quality options.

    Generate this batch as if it's the SECOND or THIRD round of testing—avoid the most generic/obvious interview questions for these skills.

    Return ONLY a JSON array of exactly 30 objects:
    [
        {{
            "skill": "Specific Skill from Target List",
            "question": "A deep-dive, scenario-based technical question (max 250 chars)",
            "options": ["Option 1", "Option 2", "Option 3", "Option 4"],
            "answer": "Exact string of the correct option",
            "difficulty": "hard"
        }}
    ]
    """

    
    response_text = call_ai(prompt, system_prompt, module='quiz')
    return clean_json_response(response_text)

def generate_coding_challenges_batch_llm(skills, jd_text="", resume_text="", count=2, difficulty="medium"):
    """
    Generate multiple unique, real-time coding challenges based on candidate profile and job requirements.
    Ensures problems are NOT static/repeated and relate to candidate experience.
    """
    if not HAS_AI:
        return []

    system_prompt = (
        "You are a technical interview architect at a top-tier tech firm. "
        "Create UNIQUE, real-world coding challenges that test practical development skills "
        "rather than generic algorithms (no FizzBuzz, No Two Sum). "
        "Focus on domain-specific logic relevant to the candidate's resume."
    )
    
    prompt = f"""
    CANDIDATE PROFILE:
    - Top Skills: {', '.join(skills)}
    - Relevant Experience/Resume Context: {resume_text[:2000] if resume_text else 'N/A'}
    
    JOB DESCRIPTION CONTEXT:
    {jd_text[:1000] if jd_text else 'Generic Technical Role'}
    
    TASK:
    Generate EXACTLY {count} UNIQUE coding challenges of '{difficulty}' difficulty. 
    Each problem MUST be different from common interview bank questions.
    
    OUTPUT REQUIREMENT:
    Return EXACTLY {count} JSON objects in a root array. 
    Failure to provide exactly {count} challenges will result in a system error.
    
    CRITICAL INSTRUCTION ON TEST WRAPPER:
    The 'test_wrapper' should be a string template using Python-style format keys.
    Use '{{input}}' if the problem takes a single argument, or individual keys like '{{records}}' if it takes multiple.
    Example: "result = my_function({{input}})" or "result = my_function({{records}}=json.loads({{records}}))" 
    Avoid language-specific class calls if possible (e.g. use "process_data({{input}})" instead of "DataProcessor.process({{input}})").
    
    Return the result EXCLUSIVELY as a JSON array of objects with this structure:
    [
      {{
        "title": "Problem Title",
        "difficulty": "{difficulty}",
        "description": "Scenario-based description...",
        "language": "python|javascript|java|cpp|go",
        "tags": ["Scenario", "Production-Ready"],
        "starter_code": "Boilerplate code...",
        "test_cases": [
          {{"input": "argument_value", "expected": "expected_return_value"}}
        ],
        "test_wrapper": "Expression to call (e.g., 'result = process_logs({{input}})')"
      }}
    ]
    """
    
    response_text = call_ai(prompt, system_prompt, module='coding')
    return clean_json_response(response_text) or []

def generate_coding_challenge_llm(skills, jd_text=""):
    """Compatibility wrapper for single challenge generation."""
    res = generate_coding_challenges_batch_llm(skills, jd_text=jd_text, count=1)
    return res[0] if res else None

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
    
    response_text = call_ai(prompt, "You are a career consultant specializing in the Indian tech job market.", module='resume')
    return clean_json_response(response_text) or []

def calculate_job_fit_llm(resume_text, jd_text, role_title="Specified Role"):
    """Calculate job fit using semantic comparison and Cosine Similarity logic."""
    if not HAS_AI:
        return None

    system_prompt = "You are an expert recruitment analyst. Use semantic vector comparison (Cosine Similarity) concepts to calculate fit."
    prompt = f"""
    Compare the Resume against the Job Description for the role: {role_title}.
    
    Analysis Model:
    1. Overall Match Score: Calculate a precise percentage (0.0 - 100.0).
    2. Breakdown Scores: Provide individual scores (0-100) for these KEYS:
       - 'technical' (Technical Skills & Tools)
       - 'experience' (Work Experience & Tenure)
       - 'projects' (Projects, Portfolio & GitHub)
       - 'education' (Academic Qualifications & CGPA)
       - 'certifications' (Relevant Professional Certifications)
    3. Insights: A narrative summary (max 3 sentences) explaining the alignment.
    4. Skill Tables: For each 'match', 'partial', and 'missing' skill, include:
       - 'weight': (0.0 - 1.0) relative importance.
       - 'impact': (0.0 - 100.0) contribution to its category.
       - 'priority': 'High', 'Medium', or 'Low' for missing skills.

    Resume Text: {resume_text[:3000]}
    Job Description: {jd_text[:3000]}

    Return ONLY a JSON object:
    {{
        "match_percentage": 0.0,
        "insights": "Detailed summary of candidate fit...",
        "breakdown": {{
            "technical": 0,
            "experience": 0,
            "projects": 0,
            "education": 0,
            "certifications": 0
        }},
        "matches": [{{ "skill": "...", "weight": 0.0, "impact": 0 }}],
        "partial": [{{ "skill": "...", "weight": 0.0, "impact": 0 }}],
        "missing": [{{ "skill": "...", "weight": 0.0, "impact": 0, "priority": "High|Medium|Low" }}],
        "recommendations": ["..."]
    }}
    """
    
    response_text = call_ai(prompt, system_prompt, module='resume')
    res = clean_json_response(response_text)
    if res:
        try:
            # Align with internal service and routes keys - PRESERVE METADATA
            return {
                "match_score": res.get("match_percentage", 0),
                "insights": res.get("insights", "No specific alignment insights generated."),
                "breakdown": res.get("breakdown", {}),
                "matches": res.get("matches", []),
                "partial_skills": res.get("partial", []),
                "missing": res.get("missing", []),
                "recommendations": res.get("recommendations", [])
            }
        except Exception as e:
            logger.error(f"Error processing job fit: {e}")
            
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
    
    response_text = call_ai(prompt, system_prompt, module='resume')
    return clean_json_response(response_text) or []
