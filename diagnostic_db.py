
import os
import sys
from datetime import datetime

# Define base path
BACKEND_PATH = os.path.abspath(os.path.join(os.getcwd(), 'skill-mind-ai', 'backend'))
sys.path.append(BACKEND_PATH)

from app import create_app, db
from app.models.models import User, OTP

app = create_app()
with app.app_context():
    print("--- Database Diagnostics ---")
    try:
        user_count = User.query.count()
        print(f"Total Users: {user_count}")
        
        otp_count = OTP.query.count()
        print(f"Total OTPs: {otp_count}")
        
        if otp_count > 0:
            latest_otp = OTP.query.order_by(OTP.created_at.desc()).first()
            print(f"Latest OTP: email={latest_otp.email}, code={latest_otp.otp_code}, expires_at={latest_otp.expires_at}")
            print(f"Current Time (UTC): {datetime.utcnow()}")
            
        users = User.query.all()
        for u in users:
            print(f"User: ID={u.id}, Username={u.username}, Email={u.email}")
            
    except Exception as e:
        print(f"Error checking database: {str(e)}")
