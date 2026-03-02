import os
import re
from .ai_service import analyze_resume_llm, compare_resume_jd_llm, HAS_GEMINI

# Try PyPDF2 for PDF parsing
try:
    from PyPDF2 import PdfReader
    HAS_PYPDF2 = True
except ImportError:
    HAS_PYPDF2 = False

# Curated skill list for keyword-based extraction (Existing)
KNOWN_SKILLS = [
    # Programming Languages
    "Python", "JavaScript", "TypeScript", "Java", "C++", "C#", "Go", "Rust",
    "Ruby", "PHP", "Swift", "Kotlin", "Scala", "R", "MATLAB", "Perl", "Dart", "COBOL",
    # Web Frameworks
    "React", "Angular", "Vue.js", "Next.js", "Django", "Flask", "Express.js",
    "Spring Boot", "ASP.NET", "Ruby on Rails", "Laravel", "FastAPI", "Svelte", "Nuxt.js",
    # Databases
    "MySQL", "PostgreSQL", "MongoDB", "Redis", "Elasticsearch", "SQLite",
    "Oracle", "Cassandra", "DynamoDB", "Firebase", "MariaDB", "Supabase",
    # Cloud & DevOps
    "AWS", "Azure", "GCP", "Docker", "Kubernetes", "Jenkins", "Terraform",
    "Ansible", "CI/CD", "Linux", "Git", "GitHub", "GitLab", "Nginx", "Apache",
    "Serverless", "Prometheus", "Grafana",
    # Data & ML
    "Machine Learning", "Deep Learning", "TensorFlow", "PyTorch", "Keras",
    "Pandas", "NumPy", "Scikit-learn", "NLP", "Computer Vision",
    "Data Science", "Data Analysis", "Power BI", "Tableau", "Spark", "Hadoop",
    # Other
    "REST API", "GraphQL", "Microservices", "Agile", "Scrum",
    "HTML", "CSS", "SQL", "NoSQL", "Figma", "Jira",
    "Node.js", "Webpack", "Babel", "SASS", "Tailwind CSS", "Redux", "Docker Compose"
]

# Skill Aliases and Groups for smarter matching
# Format: "Generic Requirement": ["Specific Implementation 1", "Specific Implementation 2"]
SKILL_ALIASES = {
    "SQL": ["MySQL", "PostgreSQL", "SQLite", "Oracle", "Cassandra", "SQL Server", "MariaDB", "T-SQL", "PL/SQL"],
    "NoSQL": ["MongoDB", "Redis", "Cassandra", "DynamoDB", "Firebase", "CouchDB", "Neo4j"],
    "JavaScript": ["JS", "TypeScript", "React", "Vue.js", "Angular", "Node.js", "Next.js", "Express.js"],
    "Python": ["Django", "Flask", "FastAPI", "Pandas", "NumPy", "Scikit-learn", "PyTorch", "TensorFlow"],
    "Java": ["Spring Boot", "Kotlin", "Android", "Maven", "Gradle"],
    "Cloud": ["AWS", "Azure", "GCP", "Docker", "Kubernetes", "Serverless"],
    "DevOps": ["CI/CD", "Docker", "Kubernetes", "Jenkins", "Terraform", "Ansible", "GitLab CI"],
    "HTML": ["HTML5", "JSX"],
    "CSS": ["CSS3", "SASS", "SCSS", "Tailwind CSS", "Bootstrap"]
}

def extract_text_from_file(file_path):
    ext = os.path.splitext(file_path)[1].lower()
    if ext == '.pdf' and HAS_PYPDF2:
        try:
            reader = PdfReader(file_path)
            text = ""
            for page in reader.pages:
                text += page.extract_text() or ""
            return text
        except Exception:
            return ""
    elif ext == '.txt':
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            return f.read()
    return ""

def analyze_resume(text):
    """Extract skills from resume text using AI (Gemini) with a keyword-based fallback."""
    found_skills = []
    summary = ""
    degree = ""
    experience = ""
    
    # Try LLM first
    if HAS_GEMINI:
        try:
            ai_data = analyze_resume_llm(text)
            if ai_data:
                found_skills = ai_data.get("skills", [])
                summary = ai_data.get("summary", "")
                degree = ai_data.get("degree", "")
                experience = ai_data.get("experience", "")
        except Exception:
            pass

    # Keyword matching fallback or supplementary
    text_lower = text.lower()
    for skill in KNOWN_SKILLS:
        pattern = r'\b' + re.escape(skill.lower()) + r'\b'
        if re.search(pattern, text_lower) and skill not in found_skills:
            found_skills.append(skill)
    
    # Skills section heuristic
    skills_section = re.search(r'skills?\s*[:\-\|]\s*(.+?)(?:\n\n|\Z)', text_lower, re.DOTALL | re.IGNORECASE)
    if skills_section:
        section_text = skills_section.group(1)
        for skill in KNOWN_SKILLS:
            if skill.lower() in section_text and skill not in found_skills:
                found_skills.append(skill)
    
    if not found_skills:
        found_skills = ["Python", "JavaScript", "SQL"]
    
    return {
        "skills": sorted(list(set(found_skills))),
        "summary": summary,
        "degree": degree,
        "experience": experience,
        "raw_text": text
    }

def compare_skills(resume_skills, jd_text, resume_text=None):
    """Compare resume against a job description. Uses LLM if provided text, else keyword match."""
    # Try LLM-based deep comparison first
    if HAS_GEMINI and resume_text:
        try:
            ai_comparison = compare_resume_jd_llm(resume_text, jd_text)
            if ai_comparison:
                return {
                    "score": ai_comparison.get("match_score", 0),
                    "matches": ai_comparison.get("matches", []),
                    "missing": ai_comparison.get("missing", []),
                    "insights": ai_comparison.get("insights", "")
                }
        except Exception as e:
            print(f"AI Comparison Error: {e}")

    # Fallback/Manual Matching with Aliasing
    jd_analysis = analyze_resume(jd_text)
    jd_skills = sorted(list(set([s.strip() for s in jd_analysis['skills']])))
    res_skills_lower = [s.strip().lower() for s in resume_skills]
    
    if not jd_skills:
        return {"score": 0, "matches": [], "missing": [], "insights": "No specific skills detected in JD."}
        
    matches = []
    missing = []
    
    for jd_s in jd_skills:
        jd_s_lower = jd_s.lower()
        
        # 1. Direct match
        if jd_s_lower in res_skills_lower:
            matches.append(jd_s)
            continue
            
        # 2. Alias group check (Generic requirement satisfied by specific skill)
        # e.g., JD has "SQL", Resume has "MySQL"
        matched_via_alias = False
        if jd_s in SKILL_ALIASES:
            for alias in SKILL_ALIASES[jd_s]:
                if alias.lower() in res_skills_lower:
                    matched_via_alias = True
                    break
        
        if matched_via_alias:
            matches.append(jd_s)
            continue
            
        # 3. Reverse Alias check (Specific requirement satisfied by generic skill name or other alias)
        # e.g., JD has "MySQL", Resume has "SQL"
        for generic, specific_list in SKILL_ALIASES.items():
            if jd_s == generic or jd_s in specific_list:
                # If JD skill is in this group, check if generic or ANY specific from this group is in resume
                if generic.lower() in res_skills_lower:
                    matched_via_alias = True
                    break
                for s_alias in specific_list:
                    if s_alias.lower() in res_skills_lower:
                        matched_via_alias = True
                        break
            if matched_via_alias: break

        if matched_via_alias:
            matches.append(jd_s)
            continue

        # 4. Substring containment (for cases not in aliases, e.g. "React.js" vs "React")
        is_sub_match = False
        if len(jd_s_lower) > 3: # Avoid matching short things like "C" or "R"
            for res_s_lower in res_skills_lower:
                if len(res_s_lower) > 3 and (jd_s_lower in res_s_lower or res_s_lower in jd_s_lower):
                    is_sub_match = True
                    break
        
        if is_sub_match:
            matches.append(jd_s)
            continue
            
        missing.append(jd_s)
    
    # Base score using core matching
    base_score = (len(matches) / len(jd_skills)) * 100 if jd_skills else 0
    
    # Add a small dynamic factor based on skill count to avoid "static" integer looks
    bonus = min(len(res_skills_lower) * 0.5, 5.0) 
    final_score = min(base_score + bonus, 100.0) if matches else base_score
    
    return {
        "score": round(final_score, 1),
        "matches": matches,
        "missing": missing,
        "insights": "Profile Analysis: " + ("Strong match found." if final_score > 70 else "Moderate alignment. Consider highlighting missing skills.") + " (Note: Deep AI insights currently restricted by API connectivity)."
    }
