from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models.models import Quiz, CodingTest, HRSession, Score, SkillGapReport, db, Resume
from datetime import datetime

scoring_bp = Blueprint('scoring', __name__)

def calculate_resume_strength(user_id):
    resume = Resume.query.filter_by(user_id=user_id).order_by(Resume.uploaded_at.desc()).first()
    if not resume:
        return 0
    text_len = len(resume.extracted_text) if resume.extracted_text else 0
    return min((text_len / 1000) * 50 + 50, 100)

@scoring_bp.route('/generate-report', methods=['POST'])
@jwt_required()
def generate_report():
    user_id = int(get_jwt_identity())
    
    # Get latest scores
    quiz = Quiz.query.filter_by(user_id=user_id).order_by(Quiz.completed_at.desc()).first()
    coding = CodingTest.query.filter_by(user_id=user_id).order_by(CodingTest.id.desc()).first()
    interview = HRSession.query.filter_by(user_id=user_id).order_by(HRSession.id.desc()).first()
    
    quiz_score = quiz.score if quiz else 0
    coding_score = coding.score if coding else 0
    interview_score = interview.sentiment_score * 100 if (interview and interview.sentiment_score) else 0
    resume_strength = calculate_resume_strength(user_id)
    
    # Weighted Score Aggregation (Total 100 Marks):
    # Resume: 10 marks (10% weight)
    # Quiz: 30 marks (30% weight)
    # Coding: 30 marks (30% weight)
    # Interview: 30 marks (30% weight)
    
    resume_marks = (resume_strength / 100) * 10
    quiz_marks = (quiz_score / 100) * 30
    coding_marks = (coding_score / 100) * 30
    interview_marks = (interview_score / 100) * 30
    
    final_score = resume_marks + quiz_marks + coding_marks + interview_marks
    
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
    
    report = Score(
        user_id=user_id,
        quiz_score=quiz_score,
        coding_score=coding_score,
        interview_score=interview_score,
        resume_strength=resume_strength,
        final_score=final_score,
        readiness_report=f"Your overall interview readiness is {final_score:.1f}%",
        skill_gaps=analysis
    )
    db.session.add(report)
    
    # Save a separate SkillGapReport record as requested
    gap_report = SkillGapReport(
        user_id=user_id,
        report_data=analysis,
        recommendations=[a['suggestion'] for a in analysis if a['status'] != 'Strong']
    )
    db.session.add(gap_report)
    db.session.commit()
    
    return jsonify({
        "final_score": final_score,
        "quiz_score": quiz_score,
        "coding_score": coding_score,
        "interview_score": interview_score,
        "resume_strength": resume_strength,
        "marks": {
            "resume": round(resume_marks, 1),
            "quiz": round(quiz_marks, 1),
            "coding": round(coding_marks, 1),
            "interview": round(interview_marks, 1),
            "total": round(final_score, 1)
        },
        "analysis": analysis,
        "report_id": report.id
    }), 200
