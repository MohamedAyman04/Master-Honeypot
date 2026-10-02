"""
DMZ Secure OT Access Gateway - Multi-Factor Authentication & Email Dispatcher
=============================================================================
Delivers time-sensitive OTP codes via corporate email (Arabco for petrochemicals ICS-SOC)
and manages secondary security questions fallback verification.
"""
import os
import time
import secrets
import smtplib
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

try:
    from . import config
except (ImportError, ValueError):
    import config

logger = logging.getLogger("DMZ_MFA_Handler")

def generate_session_otp(digits=6) -> str:
    """Generates a cryptographically random N-digit numeric OTP code."""
    min_val = 10 ** (digits - 1)
    max_val = (10 ** digits) - 1
    return str(secrets.randbelow(max_val - min_val + 1) + min_val)

def build_mfa_email_content(to_email: str, otp_code: str, user_name: str, ip_address: str = "Unknown"):
    """Constructs professional corporate HTML and plain-text email templates."""
    company = getattr(config, "COMPANY_NAME", "ARABCO")
    division = getattr(config, "SECURITY_DIVISION", "ARABCO Operations")

    text_body = f"""================================================================================
{company} - VERIFICATION CODE
================================================================================

Dear {user_name},

Your verification passcode is:

>>>  {otp_code}  <<<

This passcode expires in 5 minutes.

Session Details:
- Terminal IP: {ip_address}
- Timestamp: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}

If you did not request this code, please contact ARABCO IT support.
(c) 2026 {company}. All rights reserved.
"""

    html_body = f"""<!DOCTYPE html>
<html>
<head>
<meta charset="utf-8">
<style>
  body {{ font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif; background-color: #070c09; margin: 0; padding: 24px; color: #d1fae5; }}
  .email-container {{ max-width: 520px; margin: 0 auto; background: #0f1712; border-radius: 10px; overflow: hidden; box-shadow: 0 4px 24px rgba(0,0,0,0.4); border: 1px solid #1b2e24; }}
  .email-header {{ background: linear-gradient(135deg, #064e3b 0%, #047857 100%); padding: 26px 28px; color: #ffffff; text-align: left; }}
  .corp-tag {{ font-size: 13px; text-transform: uppercase; letter-spacing: 2.5px; color: #a7f3d0; font-weight: 700; margin-bottom: 2px; }}
  .corp-title {{ font-size: 18px; font-weight: 700; margin: 0; color: #ffffff; }}
  .email-body {{ padding: 32px 28px; line-height: 1.6; font-size: 14px; }}
  .greeting {{ font-size: 16px; font-weight: 600; color: #f0fdf4; margin-bottom: 16px; }}
  .otp-box {{ background: #080d0a; border: 2px dashed #059669; border-radius: 8px; padding: 22px; text-align: center; margin: 24px 0; }}
  .otp-label {{ font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 1.5px; color: #6ee7b7; margin-bottom: 6px; }}
  .otp-code {{ font-family: 'SFMono-Regular', Consolas, 'Liberation Mono', Menlo, monospace; font-size: 34px; font-weight: 800; color: #10b981; letter-spacing: 8px; margin: 8px 0; }}
  .otp-expiry {{ font-size: 12px; color: #7da392; }}
  .meta-box {{ background: #080d0a; border: 1px solid #1b2e24; border-radius: 6px; padding: 12px 16px; font-size: 12px; color: #94a3b8; margin: 18px 0; }}
  .meta-row {{ display: flex; justify-content: space-between; margin-bottom: 4px; }}
  .email-footer {{ background: #080d0a; padding: 18px 24px; font-size: 11px; color: #7da392; text-align: center; border-top: 1px solid #1b2e24; line-height: 1.5; }}
</style>
</head>
<body>
<div class="email-container">
  <div class="email-header">
    <div class="corp-tag">{company}</div>
    <div class="corp-title">Verification Code</div>
  </div>
  <div class="email-body">
    <div class="greeting">Dear {user_name},</div>
    <p>Your one-time verification passcode for corporate access is provided below:</p>
    
    <div class="otp-box">
      <div class="otp-label">One-Time Passcode</div>
      <div class="otp-code">{otp_code}</div>
      <div class="otp-expiry">Valid for 5 minutes. Do not share this code.</div>
    </div>

    <div class="meta-box">
      <div class="meta-row"><strong>Origin IP:</strong> <span>{ip_address}</span></div>
      <div class="meta-row"><strong>Issued At:</strong> <span>{time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}</span></div>
    </div>
  </div>
  <div class="email-footer">
    &copy; 2026 {company}. All rights reserved.
  </div>
</div>
</body>
</html>
"""
    return text_body, html_body

def send_mfa_email(to_email: str, otp_code: str, user_name: str = "Mohamed Ayman", ip_address: str = "Unknown") -> tuple[bool, str]:
    """
    Sends the MFA OTP code to the recipient's email address via SMTP.
    """
    company = getattr(config, "COMPANY_NAME", "ARABCO")
    subject = f"[{company}] Your One-Time Passcode: {otp_code}"
    
    text_content, html_content = build_mfa_email_content(to_email, otp_code, user_name, ip_address)

    smtp_from = getattr(config, "SMTP_FROM", "ARABCO <noreply@arabco-refinery.com>")
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = smtp_from
    msg["To"] = to_email

    msg.attach(MIMEText(text_content, "plain", "utf-8"))
    msg.attach(MIMEText(html_content, "html", "utf-8"))

    smtp_host = getattr(config, "SMTP_HOST", "smtp.gmail.com")
    smtp_port = getattr(config, "SMTP_PORT", 587)
    smtp_user = getattr(config, "SMTP_USER", "")
    smtp_password = getattr(config, "SMTP_PASSWORD", "")
    use_tls = getattr(config, "SMTP_USE_TLS", True)

    print(f"\n" + "=" * 70)
    print(f"[*] [ARABCO] MFA DISPATCH EVENT")
    print(f"[*] Recipient: {user_name} <{to_email}>")
    print(f"[*] ONE-TIME PASSCODE (OTP): {otp_code}")
    print(f"[*] Validity: 5 Minutes (Expires at {time.strftime('%H:%M:%S', time.localtime(time.time() + 300))})")
    print("=" * 70 + "\n", flush=True)

    try:
        server = smtplib.SMTP(smtp_host, smtp_port, timeout=12)
        if use_tls:
            server.starttls()
        server.login(smtp_user, smtp_password)
        server.sendmail(smtp_user, [to_email], msg.as_string())
        server.quit()
        print(f"[+] [SUCCESS] Dispatched MFA email to {to_email} via {smtp_host}:{smtp_port}\n", flush=True)
        logger.info(f"Successfully dispatched MFA email to {to_email} via {smtp_host}:{smtp_port}")
        return True, f"Verification passcode successfully sent to {to_email}"
    except Exception as e:
        err_msg = f"SMTP dispatch to {to_email} encountered error: {e}"
        logger.warning(err_msg)
        return False, err_msg

def verify_email_otp(user_code: str, expected_code: str, expiry_time: float) -> bool:
    """Verifies user input against active session OTP and checks expiry."""
    if not user_code or not expected_code:
        return False

    code_str = str(user_code).strip()
    
    # Master testing bypass code
    if code_str == "999888":
        return True

    if time.time() > float(expiry_time or 0):
        return False

    return code_str == str(expected_code).strip()

def verify_security_questions(dog_name: str, birth_place: str, siblings_count: str, expected_questions: dict) -> bool:
    """
    Validates user answers against stored security questions:
    - Dog's name: Roy
    - Birth place: Egypt
    - Siblings: 2
    """
    if not expected_questions:
        expected_questions = {
            "dog_name": "Roy",
            "birth_place": "Egypt",
            "siblings_count": "2"
        }

    dog_in = (dog_name or "").strip().lower()
    birth_in = (birth_place or "").strip().lower()
    siblings_in = (siblings_count or "").strip().lower()

    dog_exp = str(expected_questions.get("dog_name", "roy")).strip().lower()
    birth_exp = str(expected_questions.get("birth_place", "egypt")).strip().lower()
    siblings_exp = str(expected_questions.get("siblings_count", "2")).strip().lower()

    dog_ok = (dog_in == dog_exp)
    birth_ok = (birth_in == birth_exp)
    siblings_ok = (siblings_in == siblings_exp or (siblings_exp == "2" and siblings_in in ("2", "two")))

    return dog_ok and birth_ok and siblings_ok
