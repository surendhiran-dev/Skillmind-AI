from ..models.models import Score, Quiz, CodingTest, InterviewReport, InterviewSession, Resume, SkillGapReport, db
from datetime import datetime

def refresh_user_score(user_id):
    """
    Recalculates and updates the aggregated Score record for a user.
    Weights: 10% Resume, 30% Quiz, 30% Coding, 30% Interview.
    """
    # 1. Latest Resume Score (10% weight)
    resume = Resume.query.filter_by(user_id=user_id).order_by(Resume.uploaded_at.desc()).first()
    resume_strength = 0
    if resume:
        # If we have a resume_score, use it. Otherwise fallback to length heuristic
        if hasattr(resume, 'resume_score') and resume.resume_score:
            resume_strength = resume.resume_score
        else:
            text_len = len(resume.extracted_text) if resume.extracted_text else 0
            resume_strength = min((text_len / 1000) * 50 + 50, 100)

    # 2. Latest Quiz Score (30% weight)
    try:
        # Try sorting by completed_at if available
        quiz = Quiz.query.filter_by(user_id=user_id).order_by(Quiz.completed_at.desc()).first()
    except Exception:
        # Fallback to id if completed_at fails
        logger.warning(f"Sort by completed_at failed for user {user_id}, falling back to id.")
        quiz = Quiz.query.filter_by(user_id=user_id).order_by(Quiz.id.desc()).first()
    
    quiz_score = quiz.score if (quiz and quiz.score is not None) else 0

    # 3. Latest Coding Score (30% weight)
    coding = CodingTest.query.filter_by(user_id=user_id).order_by(CodingTest.id.desc()).first()
    coding_score = coding.score if (coding and coding.score is not None) else 0

    # 4. Latest Interview Score (30% weight)
    # Using InterviewReport (the new model)
    interview = InterviewReport.query.join(InterviewSession).filter(InterviewSession.user_id == user_id).order_by(InterviewReport.generated_at.desc()).first()
    interview_score = interview.hr_interview_score if (interview and interview.hr_interview_score is not None) else 0

    # Ensure scores are within [0, 100]
    resume_strength = max(0, min(100, resume_strength))
    quiz_score = max(0, min(100, quiz_score))
    coding_score = max(0, min(100, coding_score))
    interview_score = max(0, min(100, interview_score))

    # Weighted Calculation
    resume_marks = (resume_strength / 100) * 10
    quiz_marks = (quiz_score / 100) * 30
    coding_marks = (coding_score / 100) * 30
    interview_marks = (interview_score / 100) * 30
    
    final_score = round(resume_marks + quiz_marks + coding_marks + interview_marks, 2)

    # Classification logic for analysis
    analysis = []
    def classify(score, label):
        if score >= 80:
            return {"category": label, "status": "Strong", "suggestion": "Excellent! Keep deepening your expertise."}
        elif score >= 50:
            return {"category": label, "status": "Moderate", "suggestion": f"Good foundation. Focus on advanced {label.lower()} concepts."}
        else:
            return {"category": label, "status": "Weak", "suggestion": f"Significant improvement needed in {label.lower()}."}

    analysis.append(classify(quiz_score, "Technical Knowledge"))
    analysis.append(classify(coding_score, "Coding Skills"))
    analysis.append(classify(interview_score, "Communication"))
    analysis.append(classify(resume_strength, "Resume Quality"))

    # Update or Create Score record
    score_record = Score.query.filter_by(user_id=user_id).order_by(Score.generated_at.desc()).first()
    
    if not score_record:
        score_record = Score(user_id=user_id)
        db.session.add(score_record)
    
    score_record.quiz_score = quiz_score
    score_record.coding_score = coding_score
    score_record.interview_score = interview_score
    score_record.resume_strength = resume_strength
    score_record.final_score = final_score
    score_record.readiness_report = f"Your overall interview readiness is {final_score:.1f}%"
    score_record.skill_gaps = analysis
    score_record.generated_at = datetime.utcnow()

    db.session.commit()
    return score_record

def calculate_weighted_score(tech_count=0, experience_years=0, project_count=0, has_edu=False, cert_count=0,
                             tech_score=None, exp_score=None, proj_score=None, edu_score=None, cert_score=None):
    """
    Fresher-Focused Weighted Score Formula (Legacy support):
    30% Technical + 10% Experience + 35% Projects + 20% Education + 5% Certifications
    """
    t_score = tech_score if tech_score is not None else min((tech_count / 10) * 100, 100)
    e_score = exp_score if exp_score is not None else min((experience_years / 5) * 100, 100)
    p_score = proj_score if proj_score is not None else min(project_count * 25, 100)
    ed_score = edu_score if edu_score is not None else (100 if has_edu else 0)
    c_score = cert_score if cert_score is not None else min(cert_count * 25, 100)

    final_score = (0.3 * t_score) + (0.1 * e_score) + (0.35 * p_score) + (0.2 * ed_score) + (0.05 * c_score)
    
    return round(final_score, 1), {
        "technical": t_score,
        "experience": e_score,
        "projects": p_score,
        "education": ed_score,
        "certifications": c_score
    }
