# logic.py
import secrets
import smtplib
import logging
from datetime import datetime, timedelta
from email.mime.text import MIMEText

logger = logging.getLogger("flask-app")
otp_storage = {}  # {identifier: {"otp": ..., "expiry": ..., "purpose": ..., "data": ...}}

# SMTP config (replace with real credentials)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_EMAIL = "noreply.connectrandom@gmail.com"
SMTP_PASSWORD = "jraqlskipdwqqrtv"  # ⚠️ Gmail App Password

# ------------------ Helper Functions ------------------
def generate_otp() -> str:
    return "".join(secrets.choice("0123456789") for _ in range(6))

def send_email_otp(to_email: str, otp: str) -> bool:
    subject = f"Your ConnectRandom OTP: {otp}"
    body = f"Your ConnectRandom OTP is: {otp}\nThis code will expire in 5 minutes."
    msg = MIMEText(body)
    msg["Subject"] = subject
    msg["From"] = SMTP_EMAIL
    msg["To"] = to_email

    try:
        server = smtplib.SMTP(SMTP_SERVER, SMTP_PORT, timeout=20)
        server.starttls()
        server.login(SMTP_EMAIL, SMTP_PASSWORD)
        server.sendmail(SMTP_EMAIL, [to_email], msg.as_string())
        server.quit()
        logger.info(f"Sent OTP to {to_email}")
        return True
    except Exception:
        logger.exception("Failed to send OTP email")
        return False

def validate_age(age_raw):
    try:
        age = int(age_raw)
        if age < 18:
            return False, "Age must be 18+"
        return True, age
    except Exception:
        return False, "Invalid age"

def store_signup_otp(identifier, user_data):
    otp_code = generate_otp()
    expiry = datetime.now() + timedelta(minutes=5)
    otp_storage[identifier] = {
        "otp": otp_code,
        "expiry": expiry,
        "purpose": "signup",
        "data": user_data,
    }
    return otp_code

def verify_otp(identifier, otp_entered, User, db):
    stored = otp_storage.get(identifier)
    if not stored:
        return False, "No OTP found"

    if stored["expiry"] < datetime.now():
        otp_storage.pop(identifier, None)
        return False, "OTP expired"

    if otp_entered != stored["otp"]:
        return False, "Invalid OTP"

    # Check duplicates
    if User.query.filter_by(username=stored["data"]["username"]).first():
        return False, "Username already taken"
    if User.query.filter_by(identifier=identifier).first():
        return False, "Email already registered"

    # Save user
    new_user = User(**stored["data"], identifier=identifier)
    db.session.add(new_user)
    db.session.commit()
    otp_storage.pop(identifier, None)
    logger.info(f"User {stored['data']['username']} created successfully")
    return True, "OTP verified, user created"

def login_user(username, password, User):
    user = User.query.filter_by(username=username).first()
    if not user:
        return False, "Invalid username"
    if password != user.password_hash:
        return False, "Invalid password"
    return True, f"Welcome back, {username}!"
