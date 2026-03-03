import os
import re
import json
import logging
import functools
from .ai_service import (
    analyze_resume_llm, calculate_job_fit_llm, 
    analyze_match_explanation_llm, generate_skill_gap_recommendations_llm,
    HAS_AI
)

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

from .scoring_service import calculate_weighted_score

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

    # Log extraction results
    if text:
        print(f"DEBUG: Successfully extracted {len(text)} characters from {file_path}")
        logging.info(f"Successfully extracted {len(text)} characters from {file_path}")
    else:
        print(f"DEBUG: Failed to extract text from {file_path}")
        logging.error(f"Failed to extract text from {file_path}")

    return text

def calculate_resume_strength_score(structured_data=None, skills=None, 
                                   tech_score=None, exp_score=None, proj_score=None, edu_score=None, cert_score=None):
    """
    Delegate to modular scoring service.
    """
    # If direct scores are provided, use them. Otherwise, calculate from metadata.
    if all(s is not None for s in [tech_score, exp_score, proj_score, edu_score, cert_score]):
        final_score, breakdown = calculate_weighted_score(
            tech_score=tech_score, exp_score=exp_score, proj_score=proj_score, 
            edu_score=edu_score, cert_score=cert_score
        )
    else:
        structured_data = structured_data or {}
        skills = skills or []
        
        tech_skills = structured_data.get('technical_skills', skills)
        tech_count = len(tech_skills)
        
        exp = structured_data.get('experience', {})
        experience_years = exp.get('total_years', 0)
        
        projects = structured_data.get('projects', [])
        project_count = len(projects)
        
        edu = structured_data.get('education', [])
        has_edu = True if edu else False
        
        certs = structured_data.get('certifications', [])
        cert_count = len(certs)

        final_score, breakdown = calculate_weighted_score(tech_count, experience_years, project_count, has_edu, cert_count)
    
    return final_score, {
        "diversity": breakdown['technical'],
        "experience": breakdown['experience'],
        "projects": breakdown['projects'],
        "education": breakdown['education'],
        "certification": breakdown['certifications']
    }

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

    if HAS_AI:
        ai_data = analyze_resume_llm(text)
        if ai_data:
            result.update(ai_data)
    
    # Calculate Production-Level Strength Score
    sc = result.get('score_components', {}) # Changed raw_analysis to result
    resume_score, score_breakdown = calculate_resume_strength_score(
        tech_score=sc.get('technical', 70),
        exp_score=sc.get('experience', 60),
        proj_score=sc.get('projects', 50),
        edu_score=sc.get('education', 80),
        cert_score=sc.get('certifications', 40)
    )
    result['resume_score'] = resume_score
    result['score_breakdown'] = score_breakdown
    result['raw_text'] = text
    
    return result

def compare_skills(resume_skills, jd_text, resume_text=None, role_title="Unspecified Role"):
    """Role-specific job matching engine."""
    match_res = None
    if HAS_AI and resume_text:
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

    # Add Explainability and Recommendations if possible
    explanation = []
    recommendations = []
    if HAS_AI and resume_text:
        explanation = analyze_match_explanation_llm(resume_text, jd_text, match_res.get("match_score", 0))
        recommendations = generate_skill_gap_recommendations_llm(match_res.get("missing", []))

    return {
        "match_score": match_res.get("match_score", 0),
        "matching_skills": match_res.get("matching_skills", match_res.get("matches", [])),
        "missing_skills": match_res.get("missing_skills", match_res.get("missing", [])),
        "breakdown": match_res.get("breakdown", {}),
        "method": match_res.get("method", "Heuristic Profile Matching"),
        "insights": match_res.get("insights", "No insights available."),
        "explanation": explanation,
        "recommendations": recommendations
    }
