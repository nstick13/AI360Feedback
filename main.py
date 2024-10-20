from flask import Flask, request, session, jsonify, render_template_string, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
import openai
import os
from itsdangerous import URLSafeTimedSerializer
import uuid

# Initialize the Flask app
app = Flask(__name__)
app.secret_key = 'supersecretkey'  # For session management
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAIL_SERVER'] = 'smtp.example.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('EMAIL_USER')
app.config['MAIL_PASSWORD'] = os.getenv('EMAIL_PASS')

# Initialize the database
db = SQLAlchemy(app)

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# Initialize Flask-Mail
mail = Mail(app)

# OpenAI API key
openai.api_key = os.getenv('OPENAI_API_KEY')

# User Model
class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    email = db.Column(db.String(150), nullable=False)
    password = db.Column(db.String(150), nullable=False)

# Feedback Givers Model
class FeedbackGiver(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    email = db.Column(db.String(150), unique=False, nullable=False)
    token = db.Column(db.String(100), unique=True, nullable=False)
    completed = db.Column(db.Boolean, default=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Utility function to generate token
def generate_verification_token(email):
    serializer = URLSafeTimedSerializer(app.secret_key)
    return serializer.dumps(email, salt='email-confirm-salt')

# Utility function to verify token
def confirm_verification_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer(app.secret_key)
    try:
        email = serializer.loads(token, salt='email-confirm-salt', max_age=expiration)
    except:
        return False
    return email

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        email = request.form['email']
        password = request.form['password']

        # Check if user already exists
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash('Username or email already taken. Please choose another one.', 'danger')
            return redirect(url_for('signup'))

        # Create new user
        new_user = User(username=username, email=email, password=password)
        db.session.add(new_user)

        try:

            db.session.commit()

        except Exception as e:
                db.session.rollback()
                flash(f'An error occurred: {str(e)}', 'danger')

        # Send verification email
        token = generate_verification_token(email)
        verify_url = url_for('verify_email', token=token, _external=True)
        msg = Message('Please verify your email', sender='noreply@example.com', recipients=[email])
        msg.body = f'Click the link to verify your email: {verify_url}'

        try:

            mail.send(msg)

        except Exception as e:
                flash(f'Failed to send email: {str(e)}', 'danger')

        flash('Account created successfully. A verification email has been sent. Please verify your email to log in.', 'success')
        return redirect(url_for('login'))

    return render_template_string('''
        <h1>Sign Up</h1>
        <form method="POST">
            <label for="username">Username:</label><br>
            <input type="text" id="username" name="username" required><br><br>
            <label for="email">Email:</label><br>
            <input type="email" id="email" name="email" required><br><br>
            <label for="password">Password:</label><br>
            <input type="password" id="password" name="password" required><br><br>
            <input type="submit" value="Sign Up">
        </form>
        <a href="{{ url_for('login') }}">Already have an account? Log in here</a>
    ''')

@app.route('/verify_email/<token>')
def verify_email(token):
    try:
        email = confirm_verification_token(token)
    except:
        flash('The verification link is invalid or has expired.', 'danger')
        return redirect(url_for('signup'))

    user = User.query.filter_by(email=email).first()
    if user:
        flash('Email verified successfully! Please log in.', 'success')
        return redirect(url_for('login'))
    else:
        flash('Invalid email verification attempt.', 'danger')
        return redirect(url_for('signup'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            return redirect(url_for('dashboard'))

        flash('Invalid username or password. Please try again.', 'danger')

    return render_template_string('''
        <h1>Login</h1>
        <form method="POST">
            <label for="username">Username:</label><br>
            <input type="text" id="username" name="username" required><br><br>
            <label for="password">Password:</label><br>
            <input type="password" id="password" name="password" required><br><br>
            <input type="submit" value="Login">
        </form>
        <a href="{{ url_for('signup') }}">Don't have an account? Sign up here</a>
    ''')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('login'))

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    if request.method == 'POST':
        # Get email addresses to send invitations
        emails = request.form.getlist('emails')
        if len(emails) > 6:
            flash('You can add up to 6 unique email addresses.', 'danger')
            return redirect(url_for('dashboard'))

        # Generate unique tokens and send invitation emails
        for email in emails:
            token = str(uuid.uuid4())
            feedback_giver = FeedbackGiver(user_id=current_user.id, email=email, token=token)
            db.session.add(feedback_giver)

            try:

                db.session.commit()

            except Exception as e:
                db.session.rollback()
                flash(f'An error occurred: {str(e)}', 'danger')

            feedback_url = url_for('feedback', token=token, _external=True)
            msg = Message('Feedback Request', sender='noreply@example.com', recipients=[email])
            msg.body = f'You have been invited to provide feedback. Please click the link to start: {feedback_url}'

            try:

                mail.send(msg)

            except Exception as e:
                flash(f'Failed to send email: {str(e)}', 'danger')

        flash('Invitations have been sent successfully.', 'success')
        return redirect(url_for('dashboard'))

    # If the request is GET, return the HTML template
    return render_template_string('''
        <h1>Welcome {{ current_user.username }}</h1>
        <form id="inviteForm" method="POST">
            <div id="emailFields">
                <label for="emails">Enter up to 6 email addresses to invite for feedback:</label><br>
                <input type="email" name="emails" required><br><br>
            </div>
            <button type="button" id="addEmailField">Add Another</button><br><br>
            <input type="submit" value="Send Invitations">
        </form>
        <a href="{{ url_for('logout') }}">Logout</a>

        <script>
            document.addEventListener('DOMContentLoaded', function() {
                const maxFields = 6;
                let emailCount = 1;
                document.getElementById('addEmailField').addEventListener('click', function() {
                    if (emailCount < maxFields) {
                        const emailFieldsDiv = document.getElementById('emailFields');
                        const newField = document.createElement('div');
                        newField.innerHTML = '<input type="email" name="emails" required><br><br>';
                        emailFieldsDiv.appendChild(newField);
                        emailCount++;
                    } else {
                        alert('You can only add up to 6 email addresses.');
                    }
                });
            });
        </script>
    ''')

@app.route('/feedback/<token>', methods=['GET', 'POST'])
def feedback(token):
    feedback_giver = FeedbackGiver.query.filter_by(token=token, completed=False).first()
    if not feedback_giver:
        flash('Invalid or expired feedback link.', 'danger')
        return redirect(url_for('dashboard'))

    if request.method == 'POST':
        # Handle feedback submission here
        feedback_giver.completed = True

        try:

            db.session.commit()

        except Exception as e:
                db.session.rollback()
                flash(f'An error occurred: {str(e)}', 'danger')
        flash('Thank you for your feedback!', 'success')
        return redirect(url_for('dashboard'))

    return render_template_string('''
        <h1>Feedback for {{ feedback_giver.email }}</h1>
        <form method="POST">
            <label for="feedback">Your feedback:</label><br>
            <textarea id="feedback" name="feedback" rows="4" cols="50" required></textarea><br><br>
            <input type="submit" value="Submit Feedback">
        </form>
    ''', feedback_giver=feedback_giver)

if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Create tables if not exist
    app.run(host='0.0.0.0', port=8080)
