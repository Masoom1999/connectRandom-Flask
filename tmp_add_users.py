from main import db, app
from main import User  # or from models import User if you separated models

# Example users to add
users = [
    {"fullname": "Alice Indore", "username": "alice1", "password_hash": "pass1", "contact": "111111", "age": 25, "gender": "Female", "city": "Indore", "identifier": "alice1@example.com"},
    {"fullname": "Bob Indore", "username": "bob1", "password_hash": "pass2", "contact": "222222", "age": 28, "gender": "Male", "city": "Indore", "identifier": "bob1@example.com"},
    {"fullname": "Charlie Indore", "username": "charlie1", "password_hash": "pass3", "contact": "333333", "age": 30, "gender": "Male", "city": "Indore", "identifier": "charlie1@example.com"},
]

with app.app_context():  # ✅ use the Flask app here
    for u in users:
        if not User.query.filter_by(username=u["username"]).first():
            user = User(**u)
            db.session.add(user)
    db.session.commit()
    print("Users added successfully!")
