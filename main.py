import secrets
import smtplib
import logging
from datetime import datetime, timedelta
from email.mime.text import MIMEText

from flask import Flask, render_template, request, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_cors import CORS
from asgiref.wsgi import WsgiToAsgi

# ------------------ Setup ------------------
app = Flask(__name__)
CORS(app)

# SQLite DB setup
app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
db = SQLAlchemy(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("flask-app")

# ------------------ Models ------------------
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    fullname = db.Column(db.String(150), nullable=False)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(200), nullable=False)  # store hashed password
    contact = db.Column(db.String(20))
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    city = db.Column(db.String(100))  # add city column
    identifier = db.Column(db.String(120), unique=True, nullable=False)  # email



# Create tables if not exist
with app.app_context():
    db.create_all()

# ------------------ OTP Store ------------------
otp_storage = {}  # {email: {"otp": ..., "expiry": ..., "purpose": ..., "data": ...}}

# SMTP config (replace with your real values)
SMTP_SERVER = "smtp.gmail.com"
SMTP_PORT = 587
SMTP_EMAIL = "noreply.connectrandom@gmail.com"
SMTP_PASSWORD = "jraqlskipdwqqrtv"  # ⚠️ Gmail App Password

# ------------------ Helpers ------------------
def generate_otp() -> str:
    return "".join(secrets.choice("0123456789") for _ in range(6))

def send_email_otp(to_email: str, otp: str):
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
    except Exception:
        logger.exception("Failed to send OTP email")
        return False
    return True

# ------------------ Routes ------------------
@app.route("/")
def index():
    return render_template("index.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    message = request.args.get("message")
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]

        user = User.query.filter_by(username=username).first()
        if not user:
            return "Invalid username", 401
        if password != user.password_hash:
            return "Invalid password", 401

        return f"Welcome back, {username}!"
    return render_template("login.html", message=message)

# ------------------ Routes ------------------
@app.route("/signup", methods=["GET", "POST"])
def signup_page():
    if request.method == "POST":
        fullname = request.form.get("fullname")
        username = request.form.get("username")
        password = request.form.get("password")
        contact = request.form.get("contact")
        age_raw = request.form.get("age")
        gender = request.form.get("gender")
        identifier = request.form.get("identifier")
        city = request.form.get("city")

        logger.info(f"Signup form submitted: fullname={fullname}, username={username}, password=***, contact={contact}, age_raw={age_raw}, gender={gender}, identifier={identifier}, city={city}")

        # Validate age
        try:
            age = int(age_raw)
            if age < 18:
                return render_template("signup.html", message="Age must be 18+", 
                                       fullname=fullname, username=username,
                                       contact=contact, age=age_raw, gender=gender,
                                       identifier=identifier, city=city)
            logger.info(f"Parsed age: {age}")
        except Exception:
            logger.exception("Failed to parse age")
            return render_template("signup.html", message="Invalid age",
                                   fullname=fullname, username=username,
                                   contact=contact, age=age_raw, gender=gender,
                                   identifier=identifier, city=city)

        # Generate OTP
        otp_code = generate_otp()
        print(f"Generated OTP: {otp_code}")
        expiry = datetime.now() + timedelta(minutes=5)
        otp_storage[identifier] = {
            "otp": otp_code,
            "expiry": expiry,
            "purpose": "signup",
            "data": {
                "fullname": fullname,
                "username": username,
                "password_hash": password,  # store plain for now, or hash if desired
                "contact": contact,
                "age": age,
                "gender": gender,
                "city": city
            },
        }


        if send_email_otp(identifier, otp_code):
            logger.info(f"Sent OTP to {identifier}")
        else:
            return render_template("signup.html", message="Failed to send OTP. Try again.")

        # Redirect to OTP verification page
        return redirect(url_for("verify_otp_page", identifier=identifier))

    # GET request
    return render_template("signup.html")


@app.route("/verify_otp", methods=["GET", "POST"])
def verify_otp_page():
    identifier = request.args.get("identifier")
    stored = otp_storage.get(identifier)

    if not stored:
        logger.warning(f"No OTP data found for identifier: {identifier}")
        return redirect(url_for("signup_page"))

    logger.info(f"Accessing OTP verification page for identifier: {identifier}")

    if request.method == "POST":
        otp_entered = request.form.get("otp")
        logger.info(f"OTP entered: {otp_entered}")

        if otp_entered != stored["otp"]:
            logger.warning(f"Invalid OTP entered for {identifier}")
            return render_template("verify_otp.html", identifier=identifier, message="Invalid OTP")
        if stored["expiry"] < datetime.now():
            logger.warning(f"Expired OTP for {identifier}")
            return render_template("verify_otp.html", identifier=identifier, message="OTP expired. Please signup again.")

        # Check duplicates
        if User.query.filter_by(username=stored["data"]["username"]).first():
            return "Username already taken", 400
        if User.query.filter_by(identifier=identifier).first():
            return "Email already registered", 400

        # Save user
        new_user = User(**stored["data"], identifier=identifier)
        db.session.add(new_user)
        db.session.commit()
        otp_storage.pop(identifier, None)
        logger.info(f"User {stored['data']['username']} created successfully")

        return redirect(url_for("login", message="OTP verified successfully! Please login."))

    # GET request
    logger.info(f"Rendering OTP verification page for identifier: {identifier}")
    return render_template("verify_otp.html", identifier=identifier)

# ------------------ ASGI ------------------
asgi_app = WsgiToAsgi(app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:asgi_app", host="127.0.0.1", port=8000, reload=True)
