import os
import re
from .ai_service import analyze_resume_llm, calculate_job_fit_llm, HAS_GEMINI

# Support for PDF and DOCX
try:
    from PyPDF2 import PdfReader
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False

try:
    import docx
    HAS_DOCX = True
except ImportError:
    HAS_DOCX = False

# Curated skill list (for fallback)
KNOWN_SKILLS = [
    "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "Rust",
    "React", "Angular", "Vue.js", "Next.js", "Django", "Flask", "Node.js",
    "MySQL", "PostgreSQL", "MongoDB", "Redis", "AWS", "Azure", "GCP", "Docker",
    "Kubernetes", "CI/CD", "Machine Learning", "Deep Learning", "SQL", "NoSQL"
]

def extract_text_from_file(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    text = ""
    if ext == '.pdf' and HAS_PYPDF2:
        try:
            reader = PdfReader(file_path)
            for page in reader.pages:
                text += page.extract_text() or ""
        except Exception: pass
    elif ext == '.docx' and HAS_DOCX:
        try:
            doc = docx.Document(file_path)
            text = "\n".join([para.text for para in doc.paragraphs])
        except Exception: pass
    elif ext == '.txt':
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                text = f.read()
        except Exception: pass
    
    # Clean formatting noise
    text = re.sub(r'[^\x00-\x7F]+', ' ', text) # Remove non-ASCII
    text = re.sub(r'\s+', ' ', text).strip()
    return text

def calculate_resume_strength_score(structured_data, skills):
    """
    Formula:
    0.4 × Skill Score + 0.2 × Experience Score + 0.2 × Project Score + 0.1 × Education Score + 0.1 × Certification Score
    """
    # 1. Skill Score (Diversity & Count)
    skill_score = min((len(skills) / 10) * 100, 100)
    
    # 2. Experience Score
    exp = structured_data.get('experience', {})
    total_years = exp.get('total_years', 0)
    experience_score = min((total_years / 5) * 100, 100) # Max score at 5 years
    
    # 3. Project Score
    projects = structured_data.get('projects', [])
    project_score = min(len(projects) * 25, 100) # Max score at 4 projects
    
    # 4. Education Score
    edu = structured_data.get('education', [])
    education_score = 100 if edu else 0
    
    # 5. Certification Score
    certs = structured_data.get('certifications', [])
    cert_score = min(len(certs) * 50, 100) # Max score at 2 certs

    final_score = (0.4 * skill_score) + (0.2 * experience_score) + (0.2 * project_score) + (0.1 * education_score) + (0.1 * cert_score)
    
    breakdown = {
        "skill_score": round(skill_score, 1),
        "experience_score": round(experience_score, 1),
        "project_score": round(project_score, 1),
        "education_score": round(education_score, 1),
        "certification_score": round(cert_score, 1)
    }
    
    return round(final_score, 1), breakdown

def analyze_resume(text):
    """Full production-level analysis pipeline."""
    # Default fallback (empty or generic to avoid false 100% match)
    result = {
        "skills": [],
        "summary": "AI extraction failed. Falling back to basic parsing.",
        "structured_data": {"education": [], "experience": {"total_years": 0.0}, "projects": [], "certifications": []},
        "explainability": {},
        "resume_score": 0.0,
        "score_breakdown": {}
    }

    if HAS_GEMINI:
        ai_data = analyze_resume_llm(text)
        if ai_data:
            result.update(ai_data)
    
    # Calculate score
    score, breakdown = calculate_resume_strength_score(result['structured_data'], result['skills'])
    result['resume_score'] = score
    result['score_breakdown'] = breakdown
    result['raw_text'] = text
    
    return result

def compare_skills(resume_skills, jd_text, resume_text=None, role_title="Unspecified Role"):
    """Role-specific job matching engine."""
    match_res = None
    if HAS_GEMINI and resume_text:
        match_res = calculate_job_fit_llm(resume_text, jd_text, role_title)
    
    if not match_res:
        # Fallback to simple skill matching if AI fails or no resume text
        matches = [s for s in resume_skills if s.lower() in jd_text.lower()]
        missing = [s for s in KNOWN_SKILLS if s.lower() in jd_text.lower() and s not in matches]
        match_score = (len(matches) / max(len(matches) + len(missing), 1)) * 100
        match_res = {
            "match_score": round(match_score, 1),
            "matches": matches,
            "missing": missing,
            "insights": "Basic skill matching used (LLM unavailable or text missing)."
        }

    return {
        "match_score": match_res.get("match_score", 0),
        "matching_skills": match_res.get("matches", []),
        "missing_skills": match_res.get("missing", []),
        "insights": match_res.get("insights", "No insights available.")
    }
