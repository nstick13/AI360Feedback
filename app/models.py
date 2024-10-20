from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), nullable=False)
    feedbacks = db.relationship('Feedback', backref='user', lazy=True)
    password = db.Column(db.String(150), nullable=False)
    first_name = db.Column(db.String(150), nullable=False)
    last_name = db.Column(db.String(150), nullable=False)
    job_title = db.Column(db.String(150), nullable=True)
    company = db.Column(db.String(150), nullable=True)

class Feedback(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    giver_id = db.Column(db.Integer, db.ForeignKey('feedback_giver.id'), nullable=False)
    content = db.Column(db.Text, nullable=False)

class FeedbackGiver(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    email = db.Column(db.String(150), unique=False, nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False)
    completed = db.Column(db.Boolean, default=False)
    feedback = db.relationship('Feedback', backref='giver', lazy=True)
