from datetime import datetime
from itsdangerous import URLSafeTimedSerializer as Serializer
from flask import current_app 
from . import db
from flask_login import UserMixin
from pyvejournal.extensions import db
from flask_login import UserMixin



class User(db.Model, UserMixin):
    # These are all columns in the table
    # the argument of db.string is the max length for the string
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    image_file = db.Column(db.String(20), nullable=False, default='default.jpg')
    password = db.Column(db.String(60), nullable=False)
    # the image file and password are hashed to exactly 60 chars
    posts = db.relationship('Post', backref='author', lazy=True)
    theme = db.Column(db.String(20), nullable=False)

    def get_reset_token(self):
        
        s = Serializer(current_app.config['SECRET_KEY'])
        return s.dumps({"user_id": self.id})

    @staticmethod
    def verify_reset_token(token, max_age=1800):
        s = Serializer(current_app.config['SECRET_KEY'])
        try:
            user_id = s.loads(token, max_age=max_age)["user_id"]
        except Exception:
            return None
        return User.query.get(user_id)
    
    # magic methods are used to define how the object is printed when we use print(). It's called magic because Python automatically calls it in certain situations.
    def __repr__(self):
        return f"User('{self.username}', '{self.email}', '{self.image_file}')"

class Post(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    date_posted = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    content = db.Column(db.Text, nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)

    def __repr__(self):
        return f"Post('{self.title}', '{self.date_posted}')"