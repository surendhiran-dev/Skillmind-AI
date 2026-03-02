import os
from flask import Flask, send_from_directory, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from flask_jwt_extended import JWTManager
from flask_socketio import SocketIO
from dotenv import load_dotenv

load_dotenv(os.path.join(os.path.dirname(__file__), '..', '.env'))

db = SQLAlchemy()
jwt = JWTManager()
socketio = SocketIO(cors_allowed_origins="*")

def create_app():
    app = Flask(__name__)
    
    # Configuration
    basedir = os.path.abspath(os.path.dirname(__file__))
    app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL', f'sqlite:///{os.path.join(basedir, "..", "skill_mind.db")}')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.config['JWT_SECRET_KEY'] = os.getenv('JWT_SECRET_KEY', 'super-secret-key')
    app.config['JWT_ACCESS_TOKEN_EXPIRES'] = 60 * 60 * 24 * 7 # 7 days
    
    # Initialize extensions
    db.init_app(app)
    jwt.init_app(app)
    socketio.init_app(app)
    CORS(app)
    
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
    
    app.register_blueprint(auth_bp, url_prefix='/api/auth')
    app.register_blueprint(resume_bp, url_prefix='/api/resume')
    app.register_blueprint(interview_bp, url_prefix='/api/interview')
    app.register_blueprint(quiz_bp, url_prefix='/api/quiz')
    app.register_blueprint(coding_bp, url_prefix='/api/coding')
    app.register_blueprint(scoring_bp, url_prefix='/api/scoring')
    app.register_blueprint(dashboard_bp, url_prefix='/api/dashboard')
    
    # Import socket events to register them
    from .websocket import interview_socket
    
    # Serve frontend static files
    frontend_dir = os.path.abspath(os.path.join(basedir, '..', '..', 'frontend'))

    @app.route('/')
    def serve_index():
        return send_from_directory(frontend_dir, 'index.html')

    @app.route('/<path:filename>')
    def serve_static(filename):
        return send_from_directory(frontend_dir, filename)
    
    # Create tables on first run
    with app.app_context():
        db.create_all()
    
    return app
