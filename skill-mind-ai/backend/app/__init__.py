import os
from datetime import datetime
from flask import Flask, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

db = SQLAlchemy()
jwt = JWTManager()
socketio = SocketIO(cors_allowed_origins="*", async_mode='gevent')

def create_app():
    app = Flask(__name__)
    
    # Configuration
    basedir = os.path.abspath(os.path.dirname(__file__))
    db_url = os.getenv('DATABASE_URL', f'sqlite:///{os.path.join(basedir, "..", "skill_mind.db")}')
    
    # Fix Railway/Render MySQL URL if needed
    if db_url.startswith('mysql://'):
        db_url = db_url.replace('mysql://', 'mysql+pymysql://', 1)
    
    app.config['SQLALCHEMY_DATABASE_URI'] = db_url
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'super-secret-key')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 60 * 60 * 24 * 7 # 7 days
    
    # MySQL engine options (connection pooling + charset)
    if 'mysql' in db_url:
        app.config['SQLALCHEMY_ENGINE_OPTIONS'] = {
            'pool_recycle': 280,          # recycle connections before MySQL 5-min timeout
            'pool_pre_ping': True,        # check connection health before using
            'connect_args': {
                'charset': 'utf8mb4',
            }
        }
    
    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    socketio.init_app(app)
    # CORS Configuration
    allowed_origins = os.getenv('ALLOWED_ORIGINS', '*').split(',')
    CORS(app, resources={r"/api/*": {
        "origins": allowed_origins,
        "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        "allow_headers": ["Content-Type", "Authorization", "Access-Control-Allow-Origin"]
    }})
    
    # Debugging JWT
    @jwt.unauthorized_loader
    def unauthorized_callback(callback):
        print(f"DEBUG JWT: Unauthorized - {callback}")
        return jsonify({"message": callback}), 401

    @jwt.invalid_token_loader
    def invalid_token_callback(callback):
        return jsonify({"message": callback}), 422

    @jwt.expired_token_loader
    def expired_token_callback(jwt_header, jwt_payload):
        return jsonify({"message": "Token has expired"}), 401

    @jwt.needs_fresh_token_loader
    def fresh_token_loader_callback(jwt_header, jwt_payload):
        return jsonify({"message": "Fresh token required"}), 401

    @jwt.revoked_token_loader
    def revocable_token_loader_callback(jwt_header, jwt_payload):
        return jsonify({"message": "Token has been revoked"}), 401

    @jwt.user_lookup_error_loader
    def user_lookup_error_callback(_jwt_header, jwt_payload):
        return jsonify({"message": "User not found"}), 404
        
    @app.errorhandler(404)
    def handle_404_error(err):
        return jsonify({"message": "Not Found", "error": str(err)}), 404

    @app.errorhandler(500)
    def handle_500_error(err):
        import traceback
        with open('crash.log', 'a') as f:
            f.write(f"\n--- 500 Error at {datetime.now()} ---\n")
            f.write(traceback.format_exc())
        return jsonify({"message": "Internal Server Error", "error": str(err)}), 500

    @app.errorhandler(Exception)
    def handle_exception(e):
        from werkzeug.exceptions import HTTPException, NotFound
        if isinstance(e, NotFound):
            return jsonify({"message": "File Not Found", "error": str(e)}), 404
        if isinstance(e, HTTPException):
            return jsonify({"message": e.description, "error": str(e)}), e.code
            
        import traceback
        with open('crash.log', 'a') as f:
            f.write(f"\n--- Unhandled Exception at {datetime.now()} ---\n")
            f.write(traceback.format_exc())
        return jsonify({"message": "Unhandled Exception", "error": str(e)}), 500

    @app.errorhandler(422)
    def handle_422_error(err):
        # Often caused by signature verification failed
        message = str(err)
        if "Signature verification failed" in message:
            return jsonify({"message": "Signature verification failed. Please logout and login again."}), 422
        return jsonify({"message": message}), 422
    
    # Register blueprints
    from .routes.auth_routes import auth_bp
    from .routes.resume_routes import resume_bp
    from .routes.interview_routes import interview_bp
    from .routes.quiz_routes import quiz_bp
    from .routes.coding_routes import coding_bp
    from .routes.scoring_routes import scoring_bp
    from .routes.dashboard_routes import dashboard_bp
    from .routes.profile_routes import profile_bp
    from .routes.support_routes import support_bp
    from .routes.jobs_routes import jobs_bp
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(resume_bp, url_prefix='/api/resume')
    app.register_blueprint(interview_bp, url_prefix='/api/interview')
    app.register_blueprint(quiz_bp, url_prefix='/api/quiz')
    app.register_blueprint(coding_bp, url_prefix='/api/coding')
    app.register_blueprint(scoring_bp, url_prefix='/api/scoring')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    app.register_blueprint(profile_bp, url_prefix='/api/profile')
    app.register_blueprint(support_bp, url_prefix='/api/support')
    app.register_blueprint(jobs_bp, url_prefix='/api/jobs')

    
    # Import socket events to register them
    from .websocket import interview_socket
    
    # Serve frontend static files
    # Try multiple possible locations for frontend
    possible_frontend_dirs = [
        os.path.abspath(os.path.join(basedir, '..', '..', 'frontend')),
        os.path.abspath(os.path.join(basedir, '..', 'frontend')),
        os.path.abspath(os.path.join(os.getcwd(), 'frontend'))
    ]
    
    frontend_dir = possible_frontend_dirs[0]
    for d in possible_frontend_dirs:
        if os.path.exists(os.path.join(d, 'index.html')):
            frontend_dir = d
            break
            
    print(f"DEBUG: Serving frontend from {frontend_dir}")

    @app.route('/jobs')
    def jobs_page():
        return send_from_directory(frontend_dir, 'jobs.html')

    @app.route('/')
    def serve_index():
        if not os.path.exists(os.path.join(frontend_dir, 'index.html')):
            return jsonify({"message": "Frontend not found", "path": frontend_dir}), 404
        return send_from_directory(frontend_dir, 'index.html')

    @app.route('/<path:filename>')
    def serve_static(filename):
        # Prevent accessing sensitive files
        if filename in ['.env', 'app.py', 'package.json']:
            return jsonify({"message": "Access denied"}), 403
            
        # If file doesn't exist, return 404 instead of letting send_from_directory raise exception
        file_path = os.path.join(frontend_dir, filename)
        if not os.path.exists(file_path):
            # If it looks like a client-side route (doesn't have an extension), serve index.html
            if '.' not in filename:
                return send_from_directory(frontend_dir, 'index.html')
            return jsonify({"message": f"File {filename} not found", "path": file_path}), 404
            
        return send_from_directory(frontend_dir, filename)

    # ── Health / Diagnostics endpoint ──────────────────────────────────────
    @app.route('/api/health')
    def health_check():
        import smtplib, ssl
        status = {}

        # 1. Database check
        try:
            from sqlalchemy import text
            result = db.session.execute(text('SELECT 1')).fetchone()
            db_type = db_url.split('://')[0]
            # Count tables and users
            from .models.models import User
            user_count = User.query.count()
            status['database'] = {
                'status': '✅ Connected',
                'type': db_type,
                'user_count': user_count
            }
        except Exception as db_err:
            status['database'] = {
                'status': '❌ FAILED',
                'error': str(db_err)
            }

        # 2. Email provider check (priority matches email_service.py)
        sendgrid_key = os.getenv('SENDGRID_API_KEY', '').strip()
        resend_key   = os.getenv('RESEND_API_KEY', '').strip()
        mail_user    = os.getenv('MAIL_USERNAME', '').strip()
        mail_pass    = os.getenv('MAIL_PASSWORD', '').strip()

        if sendgrid_key:
            # SendGrid: just confirm key is set — it's always HTTP so no socket test needed
            status['email'] = {
                'status': '✅ Working',
                'mode':   'SendGrid API (Priority 1)',
                'sender': os.getenv('SENDGRID_FROM', mail_user or 'skillmindai4@gmail.com'),
                'note':   'Sends to any recipient — no domain restriction'
            }
        elif resend_key:
            status['email'] = {
                'status': '✅ Working (limited)',
                'mode':   'Resend API (no custom domain — only delivers to Resend signup email)',
                'sender': os.getenv('RESEND_FROM', 'onboarding@resend.dev'),
                'hint':   'Add SENDGRID_API_KEY to Render for unrestricted delivery'
            }
        elif mail_user and mail_pass:
            try:
                import smtplib
                with smtplib.SMTP("smtp.gmail.com", 587, timeout=10) as srv:
                    srv.ehlo(); srv.starttls(); srv.ehlo()
                    srv.login(mail_user, mail_pass)
                status['email'] = {
                    'status': '✅ Working',
                    'sender': mail_user,
                    'mode':   'Gmail SMTP (local dev only — blocked on Render)'
                }
            except Exception as smtp_err:
                status['email'] = {
                    'status': '❌ Gmail SMTP Failed',
                    'error':  str(smtp_err),
                    'hint':   'Cloud providers block SMTP. Add SENDGRID_API_KEY for production.'
                }
        else:
            status['email'] = {
                'status': '❌ NOT CONFIGURED',
                'hint':   'Add SENDGRID_API_KEY to Render environment variables.'
            }

        # 3. AI key — live test call
        ai_key = os.getenv('OPENAI_API_KEY', '').strip()
        if not ai_key:
            status['ai'] = {
                'status': '❌ Missing',
                'hint': 'Set OPENAI_API_KEY in Render Environment Variables'
            }
        else:
            # Detect key type & endpoint
            if ai_key.startswith('nvapi-'):
                key_type = 'NVIDIA NIM'
                base_url = 'https://integrate.api.nvidia.com/v1'
                test_model = 'nvidia/llama-3.1-nemotron-nano-8b-instruct'
            elif ai_key.startswith('sk-or-v1'):
                key_type = 'OpenRouter'
                base_url = 'https://openrouter.ai/api/v1'
                test_model = 'openai/gpt-4o-mini'
            elif ai_key.startswith('sk-'):
                key_type = 'OpenAI'
                base_url = 'https://api.openai.com/v1'
                test_model = 'gpt-3.5-turbo'
            else:
                key_type = 'Unknown'
                base_url = 'https://api.openai.com/v1'
                test_model = 'gpt-3.5-turbo'

            # Live test call
            try:
                from openai import OpenAI
                test_client = OpenAI(base_url=base_url, api_key=ai_key)
                resp = test_client.chat.completions.create(
                    model=test_model,
                    messages=[{"role": "user", "content": "Say OK"}],
                    max_tokens=5,
                    timeout=15
                )
                reply = resp.choices[0].message.content.strip() if resp.choices else '?'
                status['ai'] = {
                    'status': '✅ Working',
                    'key_type': key_type,
                    'base_url': base_url,
                    'model_tested': test_model,
                    'response': reply
                }
            except Exception as ai_err:
                status['ai'] = {
                    'status': '❌ API Call Failed',
                    'key_type': key_type,
                    'base_url': base_url,
                    'model_tested': test_model,
                    'error': str(ai_err)
                }
        # keep legacy field for backward compat
        status['ai_key'] = status.get('ai', {}).get('status', '❌ Missing')

        # 4. Environment
        status['environment'] = os.getenv('FLASK_ENV', 'production')

        return jsonify({'health': status}), 200

    # Create tables on first run
    with app.app_context():
        db.create_all()
    
    return app
