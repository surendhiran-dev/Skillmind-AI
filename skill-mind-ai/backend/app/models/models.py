from .. import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), default='user')
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

class Resume(db.Model):
    __tablename__ = 'resumes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    filename = db.Column(db.String(255))
    label = db.Column(db.String(50)) # e.g., 'resume1', 'resume2'
    extracted_text = db.Column(db.Text)
    
    # New Structured Fields
    structured_data = db.Column(db.JSON) # education, experience, projects, certifications
    resume_score = db.Column(db.Float, default=0.0)
    score_breakdown = db.Column(db.JSON) # diversity, experience, projects, education, certification
    skill_confidence = db.Column(db.JSON) # confidence scores and reasoning for each skill
    
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

class Skill(db.Model):
    __tablename__ = 'skills'
    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey('resumes.id'))
    skill_name = db.Column(db.String(100))
    category = db.Column(db.String(50)) # e.g., 'Technical', 'Soft'

class Quiz(db.Model):
    __tablename__ = 'quizzes'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    skill_category = db.Column(db.String(100))
    score = db.Column(db.Float)

class CodingTest(db.Model):
    __tablename__ = 'coding_tests'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    problem_statement = db.Column(db.Text)
    submitted_code = db.Column(db.Text)
    score = db.Column(db.Float)
    quality_report = db.Column(db.JSON)

class HRSession(db.Model):
    __tablename__ = 'hr_sessions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    conversation_history = db.Column(db.JSON)
    sentiment_score = db.Column(db.Float)
    final_feedback = db.Column(db.Text)

class Score(db.Model):
    __tablename__ = 'scores'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    quiz_score = db.Column(db.Float)
    coding_score = db.Column(db.Float)
    interview_score = db.Column(db.Float)
    resume_strength = db.Column(db.Float)
    final_score = db.Column(db.Float)
    readiness_report = db.Column(db.Text)
    skill_gaps = db.Column(db.JSON)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)

class SkillGapReport(db.Model):
    __tablename__ = 'skill_gap_reports'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    report_data = db.Column(db.JSON)
    recommendations = db.Column(db.JSON)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class OTP(db.Model):
    __tablename__ = 'otps'
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), nullable=False)
    otp_code = db.Column(db.String(6), nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    expires_at = db.Column(db.DateTime, nullable=False)
