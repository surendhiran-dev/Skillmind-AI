import smtplib
import os
import json
import urllib.request
import urllib.error
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from dotenv import load_dotenv

load_dotenv()

# ─────────────────────────────────────────────────────────────────────────────
#  SHARED HTML TEMPLATES
# ─────────────────────────────────────────────────────────────────────────────

def _otp_html(otp_code: str) -> str:
    return f"""
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
                font-size: 36px;
                font-weight: 700;
                color: #00d4ff;
                padding: 20px 30px;
                background-color: #f8f9fa;
                border: 2px dashed #00d4ff;
                border-radius: 12px;
                display: inline-block;
                margin: 25px 0;
                letter-spacing: 8px;
            }}
            .footer {{
                background-color: #f8f9fa;
                padding: 20px;
                text-align: center;
                font-size: 12px;
                color: #95a5a6;
            }}
            .brand {{ color: #ffffff; font-size: 24px; font-weight: bold; margin: 0; }}
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
                <p>Thank you for choosing <strong>Skill Mind AI</strong>. To complete your
                registration and secure your account, please use the following verification code:</p>
                <div style="text-align: center;">
                    <div class="otp-box">{otp_code}</div>
                </div>
                <p style="font-size: 14px; color: #7f8c8d;">
                    <strong>Note:</strong> This verification code is valid for <strong>5 minutes</strong>.
                    For your security, please do not share this code with anyone.
                </p>
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


def _cooldown_html(user_name: str) -> str:
    return f"""
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
            .content {{ padding: 40px; color: #2c3e50; line-height: 1.6; }}
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
            .brand {{ color: #ffffff; font-size: 24px; font-weight: bold; margin: 0; }}
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
                <p>Your mandatory 30-minute review and cooling-off period is now complete.
                We appreciate your patience and commitment to a fair assessment process.</p>
                <div class="tip-box">
                    <strong>&#x1F4A1; Quick Tips for Success:</strong><br>
                    &bull; Ensure your face is clearly visible and well-lit.<br>
                    &bull; Find a quiet space with minimal background noise.<br>
                    &bull; Maintain focus on the screen throughout the session.
                </div>
                <p>You can now return to your dashboard and re-join the interview whenever you are ready.</p>
                <div style="text-align: center;">
                    <a href="https://skillmind-ai.onrender.com" class="btn">Return to Dashboard</a>
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


# ─────────────────────────────────────────────────────────────────────────────
#  TRANSPORT LAYER — auto-selects provider based on env vars
# ─────────────────────────────────────────────────────────────────────────────

def _send_via_resend(to_email: str, subject: str, html_body: str) -> bool:
    """
    Send email via Resend HTTP API (works on all cloud platforms including Render).
    Requires RESEND_API_KEY in environment variables.
    Sign up free at https://resend.com — 3 000 emails / month free.
    """
    api_key = os.getenv('RESEND_API_KEY', '').strip()
    if not api_key:
        print("[EMAIL SERVICE] RESEND_API_KEY not set — cannot use Resend.")
        return False

    from_addr = os.getenv('RESEND_FROM', 'Skill Mind AI <onboarding@resend.dev>')

    payload = json.dumps({
        "from": from_addr,
        "to": [to_email],
        "subject": subject,
        "html": html_body,
    }).encode('utf-8')

    req = urllib.request.Request(
        'https://api.resend.com/emails',
        data=payload,
        headers={
            'Authorization': f'Bearer {api_key}',
            'Content-Type': 'application/json',
        },
        method='POST'
    )

    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            status = resp.status
            body = resp.read().decode('utf-8')
        if status in (200, 201):
            print(f"[EMAIL SERVICE] ✅ Email sent via Resend to {to_email}")
            return True
        else:
            print(f"[EMAIL SERVICE] Resend returned status {status}: {body}")
            return False
    except urllib.error.HTTPError as e:
        error_body = e.read().decode('utf-8')
        print(f"[EMAIL SERVICE] Resend HTTP error {e.code}: {error_body}")
        return False
    except Exception as e:
        print(f"[EMAIL SERVICE] Resend request failed: {str(e)}")
        return False


def _send_via_gmail_smtp(to_email: str, subject: str, html_body: str, text_body: str) -> bool:
    """
    Send email via Gmail SMTP (port 587 / STARTTLS).
    Works perfectly locally. On Render/cloud, Gmail may block datacenter IPs —
    use Resend instead by setting RESEND_API_KEY.
    """
    sender_email = os.getenv('MAIL_USERNAME', '').strip()
    password = os.getenv('MAIL_PASSWORD', '').strip()

    if not sender_email or not password:
        print("[EMAIL SERVICE] ERROR: MAIL_USERNAME or MAIL_PASSWORD not set in .env")
        return False

    message = MIMEMultipart("alternative")
    message["Subject"] = subject
    message["From"] = f"Skill Mind AI <{sender_email}>"
    message["To"] = to_email
    message.attach(MIMEText(text_body, "plain"))
    message.attach(MIMEText(html_body, "html"))

    try:
        print(f"[EMAIL SERVICE] Attempting Gmail SMTP (smtp.gmail.com:587) → {to_email}")
        with smtplib.SMTP("smtp.gmail.com", 587, timeout=15) as server:
            server.ehlo()
            server.starttls()
            server.ehlo()
            server.login(sender_email, password)
            server.sendmail(sender_email, to_email, message.as_string())
        print(f"[EMAIL SERVICE] ✅ Email sent via Gmail SMTP to {to_email}")
        return True
    except Exception as e:
        print(f"[EMAIL SERVICE] Gmail SMTP failed: {str(e)}")
        return False


def _send_email(to_email: str, subject: str, html_body: str, text_body: str) -> bool:
    """
    Smart transport selector:
      • If RESEND_API_KEY is set → use Resend (recommended for Render/production)
      • Otherwise              → use Gmail SMTP (recommended for local development)
    """
    resend_key = os.getenv('RESEND_API_KEY', '').strip()

    if resend_key:
        print("[EMAIL SERVICE] Provider: Resend API")
        return _send_via_resend(to_email, subject, html_body)
    else:
        print("[EMAIL SERVICE] Provider: Gmail SMTP")
        return _send_via_gmail_smtp(to_email, subject, html_body, text_body)


# ─────────────────────────────────────────────────────────────────────────────
#  PUBLIC API
# ─────────────────────────────────────────────────────────────────────────────

def send_otp_email(receiver_email: str, otp_code: str) -> bool:
    subject = f"Verification Code: {otp_code} — Skill Mind AI"
    html    = _otp_html(otp_code)
    text    = (
        f"Hello,\n\n"
        f"Your Skill Mind AI verification code is: {otp_code}\n\n"
        f"This code expires in 5 minutes. Do not share it with anyone.\n\n"
        f"Best regards,\nSkill Mind AI Team"
    )
    return _send_email(receiver_email, subject, html, text)


def send_cooldown_ready_email(receiver_email: str, user_name: str) -> bool:
    subject = "You're Ready! Your Interview Cooldown has Expired — Skill Mind AI"
    html    = _cooldown_html(user_name)
    text    = (
        f"Hello {user_name},\n\n"
        f"Your 30-minute review period is complete. You are now eligible to "
        f"re-attempt your AI Interview.\n\n"
        f"Best regards,\nSkill Mind AI Team"
    )
    return _send_email(receiver_email, subject, html, text)
