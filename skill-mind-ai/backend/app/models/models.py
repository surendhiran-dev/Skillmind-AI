from .. import db
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

class User(db.Model):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password_hash = db.Column(db.String(128))
    role = db.Column(db.String(20), default='user')
    full_name = db.Column(db.String(100))
    profile_photo = db.Column(db.Text) # Base64 or URL
    bio = db.Column(db.Text)
    phone = db.Column(db.String(20))
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
    duration = db.Column(db.Integer)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)

class CodingTest(db.Model):
    __tablename__ = 'coding_tests'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    problem_statement = db.Column(db.Text)
    submitted_code = db.Column(db.Text)
    score = db.Column(db.Float)
    quality_report = db.Column(db.JSON)
    duration = db.Column(db.Integer)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)

class HRSession(db.Model):
    __tablename__ = 'hr_sessions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    conversation_history = db.Column(db.JSON)
    sentiment_score = db.Column(db.Float)
    final_feedback = db.Column(db.Text)
    duration = db.Column(db.Integer)
    completed_at = db.Column(db.DateTime, default=datetime.utcnow)

class InterviewSession(db.Model):
    __tablename__ = 'interview_sessions'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    session_token = db.Column(db.String(64), unique=True)
    status = db.Column(db.String(20), default='started') # 'started', 'in_progress', 'completed'
    total_questions = db.Column(db.Integer, default=6)
    current_question = db.Column(db.Integer, default=0)
    termination_reason = db.Column(db.String(100)) # e.g. 'security:multi_person'
    started_at = db.Column(db.DateTime, default=datetime.utcnow)
    ended_at = db.Column(db.DateTime)

    # Added relationship for easier access in history views
    report = db.relationship('InterviewReport', backref='session', uselist=False, lazy=True)

class InterviewQA(db.Model):
    __tablename__ = 'interview_qa'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('interview_sessions.id'))
    question_number = db.Column(db.Integer)
    question_text = db.Column(db.Text)
    skill_focus = db.Column(db.String(100))
    question_type = db.Column(db.String(20)) # 'behavioral', 'technical', 'situational', 'follow_up'
    difficulty = db.Column(db.String(20)) # 'easy', 'medium', 'hard'
    answer_text = db.Column(db.Text)
    relevance_score = db.Column(db.Float)
    depth_score = db.Column(db.Float)
    communication_score = db.Column(db.Float)
    confidence_score = db.Column(db.Float)
    answer_score = db.Column(db.Float)
    ai_feedback = db.Column(db.Text)
    asked_at = db.Column(db.DateTime, default=datetime.utcnow)
    answered_at = db.Column(db.DateTime)

class InterviewReport(db.Model):
    __tablename__ = 'interview_reports'
    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.Integer, db.ForeignKey('interview_sessions.id'), unique=True)
    hr_interview_score = db.Column(db.Float)
    behavioral_rating = db.Column(db.Float)
    communication_rating = db.Column(db.Float)
    technical_rating = db.Column(db.Float)
    confidence_index = db.Column(db.Float)
    readiness_level = db.Column(db.String(30)) # 'Strong', 'Moderate', 'Needs Improvement'
    top_strengths = db.Column(db.Text) # Stored as comma-separated string or JSON
    improvement_areas = db.Column(db.Text)
    ai_summary = db.Column(db.Text)
    recommendation = db.Column(db.Text)
    generated_at = db.Column(db.DateTime, default=datetime.utcnow)

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
    expires_at = db.Column(db.DateTime, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
class AIChallenge(db.Model):
    __tablename__ = 'ai_challenges'
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    title = db.Column(db.String(200))
    difficulty = db.Column(db.String(20))
    description = db.Column(db.Text)
    language = db.Column(db.String(20))
    tags = db.Column(db.JSON)
    starter_code = db.Column(db.Text)
    test_cases = db.Column(db.JSON) # List of dicts: {"input": ..., "expected": ...}
    test_wrapper = db.Column(db.Text)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

class JobVacancy(db.Model):
    __tablename__ = 'job_vacancies'
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(200), nullable=False)
    company = db.Column(db.String(150), nullable=False)
    location = db.Column(db.String(100))
    job_type = db.Column(db.String(50))          # Full-time / Part-time / Internship / Contract / Remote
    experience_level = db.Column(db.String(50))  # Fresher / Junior / Mid / Senior / Lead
    min_readiness = db.Column(db.Integer, default=0)
    required_skills = db.Column(db.JSON)         # ["Python", "Docker", "Flask"]
    preferred_skills = db.Column(db.JSON)        # nice-to-have
    salary_min = db.Column(db.Integer)
    salary_max = db.Column(db.Integer)
    currency = db.Column(db.String(10), default='INR')
    description = db.Column(db.Text)
    apply_url = db.Column(db.String(500))
    logo_url = db.Column(db.String(500))
    posted_days_ago = db.Column(db.Integer, default=0)
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
