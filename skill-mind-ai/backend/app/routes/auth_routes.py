from flask import Blueprint, request, jsonify
from flask_jwt_extended import jwt_required, get_jwt_identity
from ..models.models import User, OTP
from .. import db
from ..services.email_service import send_otp_email
import random
from datetime import datetime, timedelta

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['POST'])
def register():
    data = request.get_json()
    if not data:
        return jsonify({"message": "No input data provided"}), 400
    
    username = data.get('username')
    email = data.get('email')
    password = data.get('password')
    otp_code = data.get('otp')
    
    if not username or not email or not password or not otp_code:
        return jsonify({"message": "Username, email, password, and OTP are required"}), 400
        
    # Verify OTP
    otp_record = OTP.query.filter_by(email=email, otp_code=otp_code).order_by(OTP.created_at.desc()).first()
    if not otp_record or otp_record.expires_at < datetime.utcnow():
        return jsonify({"message": "Invalid or expired OTP"}), 400
    
    # Delete OTP after use
    db.session.delete(otp_record)
    
    if User.query.filter_by(email=email).first():
        return jsonify({"message": f"Email '{email}' already exists"}), 400
    
    new_user = User(
        username=username,
        email=email,
        role=data.get('role', 'user')
    )
    new_user.set_password(password)
    db.session.add(new_user)
    db.session.commit()
    
    from flask_jwt_extended import create_access_token
    access_token = create_access_token(identity=str(new_user.id))
    
    return jsonify({
        "message": "User registered successfully",
        "token": access_token,
        "user": {
            "id": new_user.id,
            "username": new_user.username,
            "role": new_user.role
        }
    }), 201

@auth_bp.route('/send-otp', methods=['POST'])
def send_otp():
    import threading
    data = request.get_json()
    email = data.get('email')
    if not email:
        return jsonify({"message": "Email is required"}), 400
    
    # Generate 6-digit OTP
    otp_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
    
    # Store OTP
    expires_at = datetime.utcnow() + timedelta(minutes=1)
    new_otp = OTP(email=email, otp_code=otp_code, expires_at=expires_at)
    db.session.add(new_otp)
    db.session.commit()
    
    # Send email in a background thread so the user doesn't wait
    threading.Thread(target=send_otp_email, args=(email, otp_code)).start()
    
    return jsonify({"message": "OTP sent successfully"}), 200

@auth_bp.route('/verify-otp-instant', methods=['POST'])
def verify_otp_instant():
    data = request.get_json()
    email = data.get('email')
    otp_code = data.get('otp')
    
    if not email or not otp_code:
        return jsonify({"valid": False, "message": "Email and OTP are required"}), 400
        
    otp_record = OTP.query.filter_by(email=email, otp_code=otp_code).order_by(OTP.created_at.desc()).first()
    
    if otp_record and otp_record.expires_at > datetime.utcnow():
        return jsonify({"valid": True}), 200
    
    return jsonify({"valid": False, "message": "Invalid or expired OTP"}), 200

@auth_bp.route('/login', methods=['POST'])
def login():
    data = request.get_json()
    if not data or not data.get('email') or not data.get('password'):
        return jsonify({"message": "Email and password are required"}), 400
        
    email = data.get('email')
    user = User.query.filter_by(email=email).first()
    
    if user and user.check_password(data.get('password')):
        from flask_jwt_extended import create_access_token
        access_token = create_access_token(identity=str(user.id))
        return jsonify({
            "token": access_token,
            "user": {
                "id": user.id,
                "username": user.username,
                "role": user.role
            }
        }), 200
    
    return jsonify({"message": "Invalid email or password"}), 401


@auth_bp.route('/me', methods=['GET'])
@jwt_required()
def get_me():
    user_id = int(get_jwt_identity())
    user = User.query.get(user_id)
    if not user:
        return jsonify({"message": "User not found"}), 404
        
    return jsonify({
        "user": {
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "role": user.role
        }
    }), 200

@auth_bp.route('/forgot-password', methods=['POST'])
def forgot_password():
    data = request.get_json()
    email = data.get('email')
    if not email:
        return jsonify({"message": "Email is required"}), 400
    
    user = User.query.filter_by(email=email).first()
    if not user:
        # For security, we might not want to disclose if email exists, 
        # but in this context, it's helpful.
        return jsonify({"message": "User with this email not found"}), 404
    
    # Generate 6-digit OTP
    otp_code = ''.join([str(random.randint(0, 9)) for _ in range(6)])
    
    # Store OTP
    expires_at = datetime.utcnow() + timedelta(minutes=1)
    new_otp = OTP(email=email, otp_code=otp_code, expires_at=expires_at)
    db.session.add(new_otp)
    db.session.commit()
    
    # Send email in a background thread
    import threading
    threading.Thread(target=send_otp_email, args=(email, otp_code)).start()
    
    return jsonify({"message": "Password reset OTP sent to your email"}), 200

@auth_bp.route('/verify-reset-otp', methods=['POST'])
def verify_reset_otp():
    data = request.get_json()
    email = data.get('email')
    otp_code = data.get('otp')
    
    if not email or not otp_code:
        return jsonify({"message": "Email and OTP are required"}), 400
    
    # Verify OTP
    otp_record = OTP.query.filter_by(email=email, otp_code=otp_code).order_by(OTP.created_at.desc()).first()
    if not otp_record or otp_record.expires_at < datetime.utcnow():
        return jsonify({"message": "Invalid or expired OTP"}), 400
    
    return jsonify({"message": "OTP verified successfully"}), 200

@auth_bp.route('/reset-password', methods=['POST'])
def reset_password():
    data = request.get_json()
    email = data.get('email')
    otp_code = data.get('otp')
    new_password = data.get('password')
    
    if not email or not otp_code or not new_password:
        return jsonify({"message": "Email, OTP, and new password are required"}), 400
    
    # Verify OTP
    otp_record = OTP.query.filter_by(email=email, otp_code=otp_code).order_by(OTP.created_at.desc()).first()
    if not otp_record or otp_record.expires_at < datetime.utcnow():
        return jsonify({"message": "Invalid or expired OTP"}), 400
    
    # Update user password
    user = User.query.filter_by(email=email).first()
    if not user:
         return jsonify({"message": "User not found"}), 404
         
    user.set_password(new_password)
    db.session.delete(otp_record)
    db.session.commit()
    
    return jsonify({"message": "Password reset successful. You can now login."}), 200
