# main.py
import logging
from datetime import datetime

from flask import Flask, render_template, request, redirect, url_for
from flask_cors import CORS
from asgiref.wsgi import WsgiToAsgi

from models import db, User
import logic
from flask import session 
from flask import request, jsonify
from logic import get_conversation, save_message
from flask import request, jsonify, session
from logic import Message, db
from models import db, User, Message
# ------------------ Setup ------------------
app = Flask(__name__)
app.secret_key = "supersecretkey"
CORS(app)

# app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///users.db"
# app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False
# db.init_app(app)

app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///connectrandom.db"
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

db.init_app(app)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("flask-app")

# Create tables
with app.app_context():
    db.create_all()

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

        # Store user info in session
        session["user_id"] = user.id
        session["username"] = user.username
        session["city"] = user.city

        return redirect(url_for("user_home"))

    return render_template("login.html", message=message)

@app.route("/signup", methods=["GET", "POST"])
def signup_page():
    if request.method == "POST":
        fullname = request.form.get("fullname")
        username = request.form.get("username")
        password = request.form.get("password")
        # contact = request.form.get("contact")
        age_raw = request.form.get("age")
        gender = request.form.get("gender")
        identifier = request.form.get("identifier")
        city = request.form.get("city")

        # Validate age
        valid, age_or_msg = logic.validate_age(age_raw)
        if not valid:
            return render_template("signup.html", message=age_or_msg,
                                   fullname=fullname, username=username,
                                #    contact=contact,
                                     age=age_raw, gender=gender,
                                   identifier=identifier, city=city)
        age = age_or_msg

        user_data = {
            "fullname": fullname,
            "username": username,
            "password_hash": password,
            # "contact": contact,
            "age": age,
            "gender": gender,
            "city": city
        }

        otp_code = logic.store_signup_otp(identifier, user_data)
        if not logic.send_email_otp(identifier, otp_code):
            return render_template("signup.html", message="Failed to send OTP. Try again.")

        return redirect(url_for("verify_otp_page", identifier=identifier))
    return render_template("signup.html")

@app.route("/verify_otp", methods=["GET", "POST"])
def verify_otp_page():
    identifier = request.args.get("identifier")
    if not identifier:
        return redirect(url_for("signup_page"))

    if request.method == "POST":
        otp_entered = request.form.get("otp")
        success, msg = logic.verify_otp(identifier, otp_entered, User, db)
        if success:
            return redirect(url_for("login", message="OTP verified successfully! Please login."))
        else:
            return render_template("verify_otp.html", identifier=identifier, message=msg)

    return render_template("verify_otp.html", identifier=identifier)


@app.route("/user_home")
def user_home():
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login", message="Please login first"))

    current_user = User.query.get(user_id)
    if not current_user:
        return redirect(url_for("login", message="User not found"))

    # Get all users from the same city except current user
    city_users = User.query.filter(User.city == current_user.city, User.id != user_id).all()

    return render_template("user_home.html", user=current_user, city_users=city_users)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login", message="Logged out successfully"))

@app.route("/send_message", methods=["POST"])
def send_message():
    data = request.get_json()

    to_user = data.get("to_user")
    from_user = data.get("from_user")
    message_content = data.get("message_content")

    if not to_user or not from_user or not message_content:
        return jsonify({"status": "error", "message": "Missing data"}), 400

    msg = Message(
        to_user=to_user,
        from_user=from_user,
        message_content=message_content  # ✅ matches models.py
    )
    db.session.add(msg)
    db.session.commit()

    return jsonify({"status": "success", "message": "Message sent"})

@app.route("/get_messages/<chat_with>", methods=["GET"])
def get_messages(chat_with):
    current_user = session.get("username")  # or however you store logged-in user
    if not current_user:
        return jsonify({"status": "error", "message": "Not logged in"}), 403

    # fetch both directions of conversation
    messages = Message.query.filter(
        ((Message.from_user == current_user) & (Message.to_user == chat_with)) |
        ((Message.from_user == chat_with) & (Message.to_user == current_user))
    ).order_by(Message.timestamp.asc()).all()

    return jsonify({
        "status": "success",
        "messages": [
            {
                "id": m.message_id,
                "from_user": m.from_user,
                "to_user": m.to_user,
                "message_content": m.message_content,
                "timestamp": m.timestamp.isoformat()
            }
            for m in messages
        ]
    })


# ------------------ ASGI ------------------
asgi_app = WsgiToAsgi(app)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:asgi_app", host="127.0.0.1", port=8000, reload=True)
