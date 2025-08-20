# models.py
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime

db = SQLAlchemy()

class User(db.Model):
    __tablename__ = "user"
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password_hash = db.Column(db.String(120), nullable=False)
    fullname = db.Column(db.String(120), nullable=False)
    age = db.Column(db.Integer, nullable=False)
    gender = db.Column(db.String(10), nullable=False)
    city = db.Column(db.String(120), nullable=False)
    email = db.Column(db.String(150), unique=True, nullable=False)  # NEW FIELD

class Message(db.Model):
    __tablename__ = "messages"
    message_id = db.Column(db.Integer, primary_key=True, autoincrement=True)
    from_user = db.Column(db.String(80), nullable=False)
    to_user = db.Column(db.String(80), nullable=False)
    message_content = db.Column(db.Text, nullable=False)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
