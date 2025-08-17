import secrets
import smtplib
import logging
from datetime import datetime, timedelta
from email.mime.text import MIMEText

from flask import Flask, render_template, request, redirect, url_for
from flask_cors import CORS
from asgiref.wsgi import WsgiToAsgi

# Flask setup
app = Flask(__name__)
CORS(app)  # enable CORS
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("flask-app")

# In-memory stores
users_db = {}      # {username: {...}}
otp_storage = {}   # {identifier: {"otp": ..., "expiry": ..., "purpose": ..., "pending_user": {...}}}

# SMTP config (⚠️ replace with your real values)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_EMAIL = "noreply.connectrandom@gmail.com"
SMTP_PASSWORD = "jraqlskipdwqqrtv"   # ⚠️ replace with Gmail App Password


# ------------------ Helpers ------------------
def generate_otp() -> str:
    return ''.join(secrets.choice("0123456789") for _ in range(6))


def send_email_otp(to_email: str, otp: str):
    subject = f"Your ConnectRandom OTP: {otp}"
    body = f"Your ConnectRandom OTP is: {otp}\n\nThis code will expire in 5 minutes."
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
        logger.info(f"Sent OTP {otp} to {to_email}")
    except Exception:
        logger.exception("Failed to send OTP email")
        return False
    return True


# ------------------ Web Pages ------------------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = users_db.get(username)
        if not user:
            return render_template("login.html", message="Invalid username")

        if password != user.get("password_hash"):  # ⚠️ plain-text check for now
            return render_template("login.html", message="Invalid password")

        return f"Welcome back, {username}!"

    # If redirected with success message
    msg = request.args.get("message")
    return render_template("login.html", message=msg)


@app.route("/signup", methods=["GET", "POST"])
def signup_page():
    if request.method == "POST":
        fullname = request.form.get("fullname")
        username = request.form.get("username")
        password = request.form.get("password")
        contact = request.form.get("contact")
        age = request.form.get("age")
        gender = request.form.get("gender")
        identifier = request.form.get("identifier")  # email

        # enforce age > 18
        try:
            if int(age) < 18:
                return render_template("signup.html", message="Age must be 18 or above.")
        except Exception:
            return render_template("signup.html", message="Invalid age.")

        # Generate OTP
        otp_code = generate_otp()
        expiry = datetime.now() + timedelta(minutes=5)
        otp_storage[identifier] = {
            "otp": otp_code,
            "expiry": expiry,
            "purpose": "signup",
            "pending_user": {
                "fullname": fullname,
                "username": username,
                "password_hash": password,
                "contact": contact,
                "age": age,
                "gender": gender,
                "identifier": identifier,
            }
        }

        if not send_email_otp(identifier, otp_code):
            return render_template("signup.html", message="Some issue in generating OTP, try again later.")

        # Show verify page
        return render_template("verify_otp.html", identifier=identifier)

    return render_template("signup.html")


@app.route("/verify_otp", methods=["POST"])
def verify_otp():
    identifier = request.form.get("identifier")
    otp = request.form.get("otp")

    stored = otp_storage.get(identifier)
    if not stored or stored.get("otp") != otp or stored.get("expiry") < datetime.now():
        return render_template("verify_otp.html", identifier=identifier, message="Invalid or expired OTP.")

    # Save user
    user = stored.get("pending_user")
    if user["username"] in users_db:
        return render_template("verify_otp.html", identifier=identifier, message="Username already taken.")

    users_db[user["username"]] = user
    logger.info(f"New user created: {user['username']}")
    otp_storage.pop(identifier, None)

    # ✅ Instead of redirect with query string, render login with message
    return render_template("login.html", message="OTP verified successfully! Please login.")



# ------------------ ASGI ------------------
asgi_app = WsgiToAsgi(app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:asgi_app", host="127.0.0.1", port=8000, reload=True)
