import smtplib
import os
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

def send_otp_email(receiver_email, otp_code):
    sender_email = os.getenv('MAIL_USERNAME')
    password = os.getenv('MAIL_PASSWORD')  # This should be an App Password
    
    if not sender_email or not password:
        print("[EMAIL SERVICE] ERROR: MAIL_USERNAME or MAIL_PASSWORD not set in .env")
        return False

    message = MIMEMultipart("alternative")
    message["Subject"] = f"Verification Code: {otp_code} for Skill Mind AI"
    message["From"] = f"Skill Mind AI <{sender_email}>"
    message["To"] = receiver_email

    text = f"Hello,\n\nYour verification code for Skill Mind AI is: {otp_code}\n\nThis code will expire in 1 minute. Please do not share this code with anyone.\n\nBest regards,\nSkill Mind AI Team"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            .email-container {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 600px;
                margin: 0 auto;
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                overflow: hidden;
            }}
            .header {{
                background-color: #1a1a2e;
                padding: 30px;
                text-align: center;
            }}
            .content {{
                padding: 40px;
                color: #2c3e50;
                line-height: 1.6;
            }}
            .otp-box {{
                font-size: 32px;
                font-weight: 700;
                color: #00d4ff;
                padding: 20px;
                background-color: #f8f9fa;
                border: 2px dashed #00d4ff;
                border-radius: 12px;
                display: inline-block;
                margin: 25px 0;
                letter-spacing: 5px;
            }}
            .footer {{
                background-color: #f8f9fa;
                padding: 20px;
                text-align: center;
                font-size: 12px;
                color: #95a5a6;
            }}
            .brand {{
                color: #ffffff;
                font-size: 24px;
                font-weight: bold;
                margin: 0;
            }}
            .accent {{ color: #00d4ff; }}
        </style>
    </head>
    <body style="margin: 0; padding: 0; background-color: #f4f7f6;">
        <div class="email-container" style="margin-top: 50px; margin-bottom: 50px;">
            <div class="header">
                <h1 class="brand">SKILL MIND <span class="accent">AI</span></h1>
            </div>
            <div class="content">
                <h2 style="margin-top: 0; color: #1a1a2e;">Email Verification</h2>
                <p>Hello,</p>
                <p>Thank you for choosing <strong>Skill Mind AI</strong>. To complete your registration and secure your account, please use the following verification code:</p>
                
                <div style="text-align: center;">
                    <div class="otp-box">{otp_code}</div>
                </div>
                
                <p style="font-size: 14px; color: #7f8c8d;"><strong>Note:</strong> This verification code is valid for 1 minute. For your security, please do not share this code with anyone.</p>
                
                <p>If you did not request this verification, you can safely ignore this email.</p>
                
                <p style="margin-bottom: 0;">Best regards,</p>
                <p style="margin-top: 5px; font-weight: 600;">The Skill Mind AI Team</p>
            </div>
            <div class="footer">
                &copy; 2026 Skill Mind AI. All rights reserved.<br>
                Empowering your career growth through intelligent assessment.
            </div>
        </div>
    </body>
    </html>
    """

    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")
    message.attach(part1)
    message.attach(part2)

    try:
        # Try Port 465 (SSL) first with a specific timeout
        print(f"[EMAIL SERVICE] Attempting SSL connection to smtp.gmail.com:465...")
        with smtplib.SMTP_SSL("smtp.gmail.com", 465, timeout=10) as server:
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message.as_string())
        print(f"[EMAIL SERVICE] OTP emailed successfully via SSL to {receiver_email}")
        return True
    except Exception as e:
        print(f"[EMAIL SERVICE] SSL failed: {str(e)}. Trying Port 587 (STARTTLS)...")
        try:
            # Fallback to Port 587 with a longer timeout
            with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as server:
                server.starttls()
                server.login(sender_email, password)
                server.sendmail(sender_email, receiver_email, message.as_string())
            print(f"[EMAIL SERVICE] OTP emailed via STARTTLS to {receiver_email}")
            return True
        except Exception as starttls_e:
            print(f"[EMAIL SERVICE] STARTTLS also failed: {str(starttls_e)}. Trying alternative server...")
            try:
                # Last resort: try smtp.googlemail.com (sometimes works better on cloud IPs)
                with smtplib.SMTP_SSL("smtp.googlemail.com", 465, timeout=10) as server:
                    server.login(sender_email, password)
                    server.sendmail(sender_email, receiver_email, message.as_string())
                print(f"[EMAIL SERVICE] OTP emailed via googlemail fallback to {receiver_email}")
                return True
            except Exception as last_e:
                print(f"[EMAIL SERVICE] ALL ATTEMPTS FAILED: {str(last_e)}")
                return False
def send_cooldown_ready_email(receiver_email, user_name):
    sender_email = os.getenv('MAIL_USERNAME')
    password = os.getenv('MAIL_PASSWORD')
    
    if not sender_email or not password:
        print("[EMAIL SERVICE] ERROR: MAIL_USERNAME or MAIL_PASSWORD not set in .env")
        return False

    message = MIMEMultipart("alternative")
    message["Subject"] = "You're Ready! Your Interview Cooldown has Expired"
    message["From"] = f"Skill Mind AI <{sender_email}>"
    message["To"] = receiver_email

    text = f"Hello {user_name},\n\nYour 30-minute review period is complete, and you are now eligible to re-attempt your AI Interview. Please ensure you are in a quiet, well-lit environment for your next session.\n\nBest regards,\nSkill Mind AI Team"
    
    html = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            .email-container {{
                font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
                max-width: 600px;
                margin: 0 auto;
                background-color: #ffffff;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                overflow: hidden;
            }}
            .header {{
                background-color: #060a16;
                padding: 30px;
                text-align: center;
                border-bottom: 2px solid #1a73e8;
            }}
            .content {{
                padding: 40px;
                color: #2c3e50;
                line-height: 1.6;
            }}
            .btn {{
                padding: 15px 30px;
                background-color: #1a73e8;
                color: #ffffff !important;
                text-decoration: none;
                border-radius: 8px;
                font-weight: 700;
                display: inline-block;
                margin: 25px 0;
                text-transform: uppercase;
                letter-spacing: 1px;
            }}
            .footer {{
                background-color: #f8f9fa;
                padding: 20px;
                text-align: center;
                font-size: 12px;
                color: #95a5a6;
            }}
            .brand {{
                color: #ffffff;
                font-size: 24px;
                font-weight: bold;
                margin: 0;
            }}
            .accent {{ color: #1a73e8; }}
            .tip-box {{
                background-color: rgba(26, 115, 232, 0.05);
                border-left: 4px solid #1a73e8;
                padding: 15px;
                margin: 20px 0;
                font-size: 0.9rem;
            }}
        </style>
    </head>
    <body style="margin: 0; padding: 0; background-color: #f4f7f6;">
        <div class="email-container" style="margin-top: 50px; margin-bottom: 50px;">
            <div class="header">
                <h1 class="brand">SKILL MIND <span class="accent">AI</span></h1>
            </div>
            <div class="content">
                <h2 style="margin-top: 0; color: #060a16;">Ready for your next attempt?</h2>
                <p>Hello <strong>{user_name}</strong>,</p>
                <p>Your mandatory 30-minute review and cooling-off period is now complete. We appreciate your patience and your commitment to a fair assessment process.</p>
                
                <div class="tip-box">
                    <strong>💡 Quick Tips for Success:</strong><br>
                    • Ensure your face is clearly visible and well-lit.<br>
                    • Find a quiet space with minimal background noise.<br>
                    • Maintain focus on the screen throughout the session.
                </div>
                
                <p>You can now return to your dashboard and re-join the interview whenever you are ready.</p>
                
                <div style="text-align: center;">
                    <a href="http://localhost:8000" class="btn">Return to Dashboard</a>
                </div>
                
                <p style="margin-bottom: 0;">Best of luck!</p>
                <p style="margin-top: 5px; font-weight: 600;">The Skill Mind AI Team</p>
            </div>
            <div class="footer">
                &copy; 2026 Skill Mind AI. All rights reserved.<br>
                Intelligent Capability Assessment System
            </div>
        </div>
    </body>
    </html>
    """

    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")
    message.attach(part1)
    message.attach(part2)

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender_email, password)
            server.sendmail(sender_email, receiver_email, message.as_string())
        print(f"[EMAIL SERVICE] Cooldown notification sent successfully to {receiver_email}")
        return True
    except Exception as e:
        print(f"[EMAIL SERVICE] ERROR sending cooldown email: {str(e)}")
        return False
