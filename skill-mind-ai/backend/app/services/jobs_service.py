import json
from ..models.models import JobVacancy, Score, Resume, Skill, User, InterviewReport, InterviewSession, db

# ── readiness helpers ────────────────────────────────────────────────────────
def _readiness_level(score):
    if score >= 75: return "Strong"
    if score >= 50: return "Moderate"
    return "Needs Improvement"

def _exp_level_score(level):
    return {"Fresher": 0, "Junior": 25, "Mid": 50, "Senior": 75, "Lead": 100}.get(level, 50)

def _normalize(s):
    return s.strip().lower()

# ── main recommendation engine ───────────────────────────────────────────────
def get_recommendations(candidate_id):
    user = User.query.get(candidate_id)
    if not user:
        return None

    score_rec = Score.query.filter_by(user_id=candidate_id).order_by(Score.generated_at.desc()).first()
    readiness_score = round(score_rec.final_score, 1) if score_rec else 0
    quiz_score      = score_rec.quiz_score      if score_rec else 0
    coding_score    = score_rec.coding_score    if score_rec else 0
    interview_score = score_rec.interview_score if score_rec else 0
    resume_strength = score_rec.resume_strength if score_rec else 0

    # candidate skills from resume
    resume = Resume.query.filter_by(user_id=candidate_id).order_by(Resume.uploaded_at.desc()).first()
    raw_skills = []
    if resume:
        raw_skills = [s.skill_name for s in Skill.query.filter_by(resume_id=resume.id).all()]
    candidate_skills_norm = set(_normalize(s) for s in raw_skills)

    # classify strong vs weak from score_rec.skill_gaps analysis
    strong_skills, weak_skills = [], []
    if score_rec and score_rec.skill_gaps:
        for item in score_rec.skill_gaps:
            if isinstance(item, dict):
                cat = item.get("category", "")
                if item.get("status") == "Strong":
                    strong_skills.append(cat)
                else:
                    weak_skills.append(cat)

    jobs = JobVacancy.query.filter_by(is_active=True).filter(JobVacancy.min_readiness <= readiness_score).all()

    scored_jobs = []
    for job in jobs:
        req = [_normalize(s) for s in (job.required_skills or [])]
        if not req:
            continue

        matched = [s for s in req if s in candidate_skills_norm]
        missing = [s for s in req if s not in candidate_skills_norm]

        overlap_pct = len(matched) / len(req) if req else 0

        job_level_score = _exp_level_score(job.experience_level)
        candidate_level_score = min(readiness_score, 100)
        level_diff = abs(job_level_score - candidate_level_score)
        readiness_fit = max(0, 1 - level_diff / 100)

        exp_mapping = {"Fresher": 10, "Junior": 30, "Mid": 50, "Senior": 75, "Lead": 90}
        exp_threshold = exp_mapping.get(job.experience_level, 50)
        experience_fit = 1.0 if readiness_score >= exp_threshold else readiness_score / max(exp_threshold, 1)
        experience_fit = min(experience_fit, 1.0)

        match_score = round(
            (overlap_pct * 0.50 + readiness_fit * 0.30 + experience_fit * 0.20) * 100, 1
        )
        skill_gap_pct = round(len(missing) / len(req) * 100, 1) if req else 0

        scored_jobs.append({
            "id": job.id,
            "title": job.title,
            "company": job.company,
            "location": job.location,
            "job_type": job.job_type,
            "experience_level": job.experience_level,
            "salary_min": job.salary_min,
            "salary_max": job.salary_max,
            "currency": job.currency,
            "required_skills": job.required_skills or [],
            "preferred_skills": job.preferred_skills or [],
            "description": job.description,
            "apply_url": job.apply_url,
            "logo_url": job.logo_url,
            "posted_days_ago": job.posted_days_ago,
            "match_score": match_score,
            "matched_skills": matched,
            "missing_skills": missing,
            "skill_gap_pct": skill_gap_pct,
        })

    scored_jobs.sort(key=lambda x: x["match_score"], reverse=True)
    top_jobs = scored_jobs[:20]

    strong  = sum(1 for j in top_jobs if j["match_score"] >= 80)
    good    = sum(1 for j in top_jobs if 60 <= j["match_score"] < 80)
    partial = sum(1 for j in top_jobs if j["match_score"] < 60)

    missing_across = {}
    for j in top_jobs:
        for s in j["missing_skills"]:
            missing_across[s] = missing_across.get(s, 0) + 1
    top_missing = sorted(missing_across, key=missing_across.get, reverse=True)[:8]

    companies = list({j["company"] for j in top_jobs})[:10]

    return {
        "candidate": {
            "name": user.full_name or user.username,
            "readiness_score": readiness_score,
            "readiness_level": _readiness_level(readiness_score),
            "strong_skills": strong_skills,
            "weak_skills": weak_skills,
            "resume_score": round(resume_strength, 1),
            "quiz_score": round(quiz_score, 1),
            "coding_score": round(coding_score, 1),
            "interview_score": round(interview_score, 1),
            "skills": raw_skills,
        },
        "jobs": top_jobs,
        "stats": {
            "total_matched": len(top_jobs),
            "strong_match": strong,
            "good_match": good,
            "partial_match": partial,
            "top_missing_skills": top_missing,
            "top_companies": companies,
        }
    }

# ── seed data ────────────────────────────────────────────────────────────────
SEED_JOBS = [
    {
        "title": "Software Engineer – Backend",
        "company": "Flipkart",
        "location": "Bengaluru",
        "job_type": "Full-time",
        "experience_level": "Junior",
        "min_readiness": 30,
        "required_skills": ["Python", "REST API", "SQL", "Git", "Linux"],
        "preferred_skills": ["Kafka", "Redis", "Docker"],
        "salary_min": 800000, "salary_max": 1400000, "currency": "INR",
        "description": "Build and scale backend services powering India's largest e-commerce platform. You will design RESTful APIs, optimise SQL queries, and collaborate with frontend and DevOps teams.",
        "apply_url": "https://www.flipkartcareers.com",
        "logo_url": "https://logo.clearbit.com/flipkart.com",
        "posted_days_ago": 2,
    },
    {
        "title": "Full Stack Developer",
        "company": "Razorpay",
        "location": "Bengaluru",
        "job_type": "Full-time",
        "experience_level": "Junior",
        "min_readiness": 35,
        "required_skills": ["React", "Node.js", "JavaScript", "REST API", "MongoDB"],
        "preferred_skills": ["TypeScript", "Redis", "AWS"],
        "salary_min": 900000, "salary_max": 1600000, "currency": "INR",
        "description": "Design and build fintech products used by 8M+ businesses. You'll work on payment dashboards, fraud-detection UIs, and high-availability microservices.",
        "apply_url": "https://razorpay.com/jobs",
        "logo_url": "https://logo.clearbit.com/razorpay.com",
        "posted_days_ago": 1,
    },
    {
        "title": "Data Scientist",
        "company": "PhonePe",
        "location": "Bengaluru",
        "job_type": "Full-time",
        "experience_level": "Mid",
        "min_readiness": 50,
        "required_skills": ["Python", "Machine Learning", "SQL", "Pandas", "Scikit-learn"],
        "preferred_skills": ["PySpark", "Airflow", "Tableau"],
        "salary_min": 1400000, "salary_max": 2400000, "currency": "INR",
        "description": "Build ML models that power UPI fraud detection and personalisation for 500M+ users. You'll own models end-to-end from feature engineering to production deployment.",
        "apply_url": "https://phonepe.com/en-in/careers",
        "logo_url": "https://logo.clearbit.com/phonepe.com",
        "posted_days_ago": 4,
    },
    {
        "title": "DevOps Engineer",
        "company": "Infosys",
        "location": "Hyderabad",
        "job_type": "Full-time",
        "experience_level": "Mid",
        "min_readiness": 45,
        "required_skills": ["Docker", "Kubernetes", "CI/CD", "Linux", "AWS"],
        "preferred_skills": ["Terraform", "Prometheus", "Ansible"],
        "salary_min": 1000000, "salary_max": 1800000, "currency": "INR",
        "description": "Manage cloud infrastructure and automate deployments for enterprise clients. Drive CI/CD pipelines, incident response, and SRE practices.",
        "apply_url": "https://infosys.com/careers",
        "logo_url": "https://logo.clearbit.com/infosys.com",
        "posted_days_ago": 5,
    },
    {
        "title": "Frontend Developer",
        "company": "Swiggy",
        "location": "Bengaluru",
        "job_type": "Full-time",
        "experience_level": "Fresher",
        "min_readiness": 20,
        "required_skills": ["HTML", "CSS", "JavaScript", "React"],
        "preferred_skills": ["TypeScript", "Redux", "Webpack"],
        "salary_min": 600000, "salary_max": 1000000, "currency": "INR",
        "description": "Craft delightful UI experiences for Swiggy's consumer app. You'll implement pixel-perfect designs, optimise Core Web Vitals, and A/B test new features.",
        "apply_url": "https://bytes.swiggy.com/careers",
        "logo_url": "https://logo.clearbit.com/swiggy.com",
        "posted_days_ago": 3,
    },
    {
        "title": "ML Engineer",
        "company": "Google India",
        "location": "Hyderabad",
        "job_type": "Full-time",
        "experience_level": "Senior",
        "min_readiness": 70,
        "required_skills": ["Python", "TensorFlow", "Machine Learning", "Deep Learning", "SQL"],
        "preferred_skills": ["JAX", "Kubernetes", "GCP"],
        "salary_min": 2500000, "salary_max": 4500000, "currency": "INR",
        "description": "Design large-scale ML systems for Google Search and Assistant. Lead model training infrastructure, champion reproducibility, and mentor junior engineers.",
        "apply_url": "https://careers.google.com",
        "logo_url": "https://logo.clearbit.com/google.com",
        "posted_days_ago": 7,
    },
    {
        "title": "Backend Developer (Go)",
        "company": "CRED",
        "location": "Bengaluru",
        "job_type": "Full-time",
        "experience_level": "Mid",
        "min_readiness": 50,
        "required_skills": ["Go", "Microservices", "REST API", "PostgreSQL", "Docker"],
        "preferred_skills": ["Kafka", "Redis", "gRPC"],
        "salary_min": 1500000, "salary_max": 2600000, "currency": "INR",
        "description": "Build high-throughput payment and rewards services in Go. Own services from design reviews to on-call rotations.",
        "apply_url": "https://careers.cred.club",
        "logo_url": "https://logo.clearbit.com/cred.club",
        "posted_days_ago": 6,
    },
    {
        "title": "Android Developer",
        "company": "Paytm",
        "location": "Noida",
        "job_type": "Full-time",
        "experience_level": "Junior",
        "min_readiness": 30,
        "required_skills": ["Java", "Kotlin", "Android SDK", "REST API", "Git"],
        "preferred_skills": ["Jetpack Compose", "Coroutines", "Firebase"],
        "salary_min": 800000, "salary_max": 1500000, "currency": "INR",
        "description": "Develop features for Paytm's Android super-app used by 300M+ users. Work on payments, lending, and commerce modules.",
        "apply_url": "https://paytm.com/careers",
        "logo_url": "https://logo.clearbit.com/paytm.com",
        "posted_days_ago": 3,
    },
    {
        "title": "iOS Developer",
        "company": "MakeMyTrip",
        "location": "Gurugram",
        "job_type": "Full-time",
        "experience_level": "Junior",
        "min_readiness": 30,
        "required_skills": ["Swift", "Xcode", "REST API", "Git", "UIKit"],
        "preferred_skills": ["SwiftUI", "Combine", "Core Data"],
        "salary_min": 850000, "salary_max": 1600000, "currency": "INR",
        "description": "Build iOS features for India's leading travel platform. Ship hotel booking flows, real-time fare tracking, and offline trip management.",
        "apply_url": "https://careers.makemytrip.com",
        "logo_url": "https://logo.clearbit.com/makemytrip.com",
        "posted_days_ago": 8,
    },
    {
        "title": "QA / Test Engineer",
        "company": "Wipro",
        "location": "Chennai",
        "job_type": "Full-time",
        "experience_level": "Fresher",
        "min_readiness": 15,
        "required_skills": ["Manual Testing", "Selenium", "Python", "SQL", "JIRA"],
        "preferred_skills": ["Cypress", "API Testing", "Postman"],
        "salary_min": 400000, "salary_max": 700000, "currency": "INR",
        "description": "Ensure quality of enterprise software through manual and automated testing. Write test plans, bug reports, and Selenium scripts.",
        "apply_url": "https://careers.wipro.com",
        "logo_url": "https://logo.clearbit.com/wipro.com",
        "posted_days_ago": 10,
    },
    {
        "title": "Cloud Solutions Architect",
        "company": "Microsoft India",
        "location": "Hyderabad",
        "job_type": "Full-time",
        "experience_level": "Senior",
        "min_readiness": 72,
        "required_skills": ["Azure", "Kubernetes", "Terraform", "Networking", "Python"],
        "preferred_skills": ["AWS", "GCP", "Service Mesh"],
        "salary_min": 2800000, "salary_max": 5000000, "currency": "INR",
        "description": "Help enterprise customers design cloud-native architectures on Azure. Lead solution workshops, PoCs, and migrations.",
        "apply_url": "https://careers.microsoft.com",
        "logo_url": "https://logo.clearbit.com/microsoft.com",
        "posted_days_ago": 2,
    },
    {
        "title": "Software Engineer Intern",
        "company": "Zepto",
        "location": "Mumbai",
        "job_type": "Internship",
        "experience_level": "Fresher",
        "min_readiness": 10,
        "required_skills": ["Python", "JavaScript", "SQL", "Git"],
        "preferred_skills": ["React", "Flask", "MongoDB"],
        "salary_min": 40000, "salary_max": 80000, "currency": "INR",
        "description": "6-month internship on Zepto's product & engineering teams. Ship real features, learn from senior engineers, and enjoy an accelerated learning curve.",
        "apply_url": "https://zepto.com/careers",
        "logo_url": "https://logo.clearbit.com/zepto.com",
        "posted_days_ago": 1,
    },
    {
        "title": "Product Manager",
        "company": "Meesho",
        "location": "Bengaluru",
        "job_type": "Full-time",
        "experience_level": "Mid",
        "min_readiness": 50,
        "required_skills": ["Product Strategy", "SQL", "Analytics", "Wireframing", "Stakeholder Management"],
        "preferred_skills": ["Python", "A/B Testing", "Figma"],
        "salary_min": 2000000, "salary_max": 3500000, "currency": "INR",
        "description": "Define and ship product features for Meesho's social commerce platform. Drive OKRs, run experiments, and champion the user voice.",
        "apply_url": "https://meesho.com/careers",
        "logo_url": "https://logo.clearbit.com/meesho.com",
        "posted_days_ago": 5,
    },
    {
        "title": "UI/UX Designer",
        "company": "Zomato",
        "location": "Gurugram",
        "job_type": "Full-time",
        "experience_level": "Junior",
        "min_readiness": 25,
        "required_skills": ["Figma", "Wireframing", "User Research", "Prototyping", "Design Systems"],
        "preferred_skills": ["After Effects", "Framer", "HTML", "CSS"],
        "salary_min": 700000, "salary_max": 1300000, "currency": "INR",
        "description": "Design end-to-end flows for Zomato's consumer and restaurant-partner apps. Collaborate with PMs, conduct usability studies, and iterate rapidly.",
        "apply_url": "https://www.zomato.com/careers",
        "logo_url": "https://logo.clearbit.com/zomato.com",
        "posted_days_ago": 4,
    },
    {
        "title": "Data Engineer",
        "company": "Ola",
        "location": "Bengaluru",
        "job_type": "Full-time",
        "experience_level": "Mid",
        "min_readiness": 45,
        "required_skills": ["Python", "PySpark", "SQL", "Airflow", "AWS"],
        "preferred_skills": ["Kafka", "dbt", "Redshift"],
        "salary_min": 1200000, "salary_max": 2200000, "currency": "INR",
        "description": "Build real-time and batch data pipelines that fuel Ola's pricing, ETA, and driver-allocation models. Own data quality SLAs and observability.",
        "apply_url": "https://ola.com/careers",
        "logo_url": "https://logo.clearbit.com/olacabs.com",
        "posted_days_ago": 6,
    },
    {
        "title": "Senior Software Engineer",
        "company": "Amazon India",
        "location": "Hyderabad",
        "job_type": "Full-time",
        "experience_level": "Senior",
        "min_readiness": 68,
        "required_skills": ["Java", "AWS", "Microservices", "System Design", "SQL"],
        "preferred_skills": ["DynamoDB", "Lambda", "Kafka"],
        "salary_min": 2200000, "salary_max": 4000000, "currency": "INR",
        "description": "Lead design and development of Amazon's supply-chain services. Drive tech-doc reviews, mentor engineers, and hold the bar for operational excellence.",
        "apply_url": "https://amazon.jobs/en/locations/india",
        "logo_url": "https://logo.clearbit.com/amazon.com",
        "posted_days_ago": 3,
    },
    {
        "title": "Security Engineer",
        "company": "HackerOne",
        "location": "Remote",
        "job_type": "Remote",
        "experience_level": "Mid",
        "min_readiness": 55,
        "required_skills": ["Python", "Penetration Testing", "Linux", "Networking", "OWASP"],
        "preferred_skills": ["Burp Suite", "Metasploit", "AWS Security"],
        "salary_min": 1600000, "salary_max": 2800000, "currency": "INR",
        "description": "Triage vulnerability reports, conduct internal red-team exercises, and build security tooling. Work remotely with a global security community.",
        "apply_url": "https://www.hackerone.com/jobs",
        "logo_url": "https://logo.clearbit.com/hackerone.com",
        "posted_days_ago": 9,
    },
    {
        "title": "Blockchain Developer",
        "company": "CoinDCX",
        "location": "Mumbai",
        "job_type": "Full-time",
        "experience_level": "Mid",
        "min_readiness": 50,
        "required_skills": ["Solidity", "Python", "Ethereum", "REST API", "Git"],
        "preferred_skills": ["Web3.js", "Hardhat", "IPFS"],
        "salary_min": 1500000, "salary_max": 2700000, "currency": "INR",
        "description": "Build smart contracts and DeFi protocols on Ethereum and Polygon. Conduct audits, optimise gas costs, and integrate with CoinDCX's exchange APIs.",
        "apply_url": "https://coindcx.com/careers",
        "logo_url": "https://logo.clearbit.com/coindcx.com",
        "posted_days_ago": 11,
    },
    {
        "title": "Site Reliability Engineer",
        "company": "Juspay",
        "location": "Bengaluru",
        "job_type": "Full-time",
        "experience_level": "Mid",
        "min_readiness": 48,
        "required_skills": ["Linux", "Kubernetes", "Python", "Prometheus", "CI/CD"],
        "preferred_skills": ["Haskell", "Grafana", "AWS"],
        "salary_min": 1300000, "salary_max": 2200000, "currency": "INR",
        "description": "Own uptime and performance for India's largest payment-routing engine. Reduce toil through automation, run chaos experiments, and improve observability.",
        "apply_url": "https://juspay.in/jobs",
        "logo_url": "https://logo.clearbit.com/juspay.in",
        "posted_days_ago": 7,
    },
    {
        "title": "Technical Lead – Full Stack",
        "company": "Freshworks",
        "location": "Chennai",
        "job_type": "Full-time",
        "experience_level": "Lead",
        "min_readiness": 78,
        "required_skills": ["Ruby on Rails", "React", "PostgreSQL", "System Design", "AWS"],
        "preferred_skills": ["Kafka", "Elasticsearch", "Redis"],
        "salary_min": 3000000, "salary_max": 5500000, "currency": "INR",
        "description": "Lead a cross-functional squad building Freshdesk's next-gen ticketing engine. Set technical direction, drive architectural decisions, and grow junior engineers.",
        "apply_url": "https://freshworks.com/company/careers",
        "logo_url": "https://logo.clearbit.com/freshworks.com",
        "posted_days_ago": 5,
    },
]

def seed_jobs():
    if JobVacancy.query.count() > 0:
        return {"message": "Already seeded", "count": JobVacancy.query.count()}
    for j in SEED_JOBS:
        db.session.add(JobVacancy(**j))
    db.session.commit()
    return {"message": "Seeded successfully", "count": len(SEED_JOBS)}

def get_all_jobs():
    jobs = JobVacancy.query.filter_by(is_active=True).order_by(JobVacancy.posted_days_ago).all()
    return [
        {
            "id": j.id, "title": j.title, "company": j.company,
            "location": j.location, "job_type": j.job_type,
            "experience_level": j.experience_level,
            "min_readiness": j.min_readiness,
            "required_skills": j.required_skills,
            "preferred_skills": j.preferred_skills,
            "salary_min": j.salary_min, "salary_max": j.salary_max,
            "currency": j.currency, "description": j.description,
            "apply_url": j.apply_url, "logo_url": j.logo_url,
            "posted_days_ago": j.posted_days_ago,
        }
        for j in jobs
    ]
