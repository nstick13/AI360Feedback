from flask import Blueprint, request, render_template_string, redirect, url_for, flash
from flask_login import login_user, logout_user, login_required, current_user
from .models import db, User
from flask_mail import Message
from itsdangerous import URLSafeTimedSerializer

auth_bp = Blueprint('auth', __name__)

# Add your signup, login, logout, and email verification routes here.

# Utility function to generate token
def generate_verification_token(email):
    serializer = URLSafeTimedSerializer('supersecretkey')  # Replace with the actual app secret key
    return serializer.dumps(email, salt='email-confirm-salt')

# Utility function to verify token
def confirm_verification_token(token, expiration=3600):
    serializer = URLSafeTimedSerializer('supersecretkey')  # Replace with the actual app secret key
    try:
        email = serializer.loads(token, salt='email-confirm-salt', max_age=expiration)
    except:
        return False
    return email

@auth_bp.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        first_name = request.form['first_name']
        last_name = request.form['last_name']
        email = request.form['email']
        password = request.form['password']
        job_title = request.form.get('job_title')
        company = request.form.get('company')

        # Check if user already exists
        existing_user = User.query.filter((User.username == username) | (User.email == email)).first()
        if existing_user:
            flash('Username or email already taken. Please choose another one.', 'danger')
            return redirect(url_for('auth.signup'))

        # Create new user
        new_user = User(username=username, first_name=first_name, last_name=last_name, email=email, password=password, job_title=job_title, company=company)
        db.session.add(new_user)

        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'danger')

        # Send verification email
        token = generate_verification_token(email)
        verify_url = url_for('auth.verify_email', token=token, _external=True)
        msg = Message('Please verify your email', sender=('Feedback App', 'your_email_here@example.com'), recipients=[email])
        msg.body = f'Click the link to verify your email: {verify_url}'

        try:
            mail.send(msg)
        except Exception as e:
            flash(f'Failed to send email to {email}: {str(e)}', 'danger')

        flash('Account created successfully. A verification email has been sent. Please verify your email to log in.', 'success')
        return redirect(url_for('auth.login'))

    return render_template_string('''
        <h1>Sign Up</h1>
        <form method="POST">
            <label for="first_name">First Name:</label><br>
            <input type="text" id="first_name" name="first_name" required><br><br>
            <label for="last_name">Last Name:</label><br>
            <input type="text" id="last_name" name="last_name" required><br><br>
            <label for="job_title">Job Title:</label><br>
            <input type="text" id="job_title" name="job_title"><br><br>
            <label for="company">Company:</label><br>
            <input type="text" id="company" name="company"><br><br>
            <label for="username">Username:</label><br>
            <input type="text" id="username" name="username" required><br><br>
            <label for="email">Email:</label><br>
            <input type="email" id="email" name="email" required><br><br>
            <label for="password">Password:</label><br>
            <input type="password" id="password" name="password" required><br><br>
            <input type="submit" value="Sign Up">
        </form>
        <a href="{{ url_for('auth.login') }}">Already have an account? Log in here</a>
    ''')

@auth_bp.route('/verify_email/<token>')
def verify_email(token):
    try:
        email = confirm_verification_token(token)
    except:
        flash('The verification link is invalid or has expired.', 'danger')
        return redirect(url_for('auth.signup'))

    user = User.query.filter_by(email=email).first()
    if user:
        flash('Email verified successfully! Please log in.', 'success')
        return redirect(url_for('auth.login'))
    else:
        flash('Invalid email verification attempt.', 'danger')
        return redirect(url_for('auth.signup'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']

        user = User.query.filter_by(username=username).first()
        if user and user.password == password:
            login_user(user)
            return redirect(url_for('command_center.command_center'))  # Updated redirect to command center

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
        <a href="{{ url_for('auth.signup') }}">Don't have an account? Sign up here</a>
    ''')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    if request.method == 'POST':
        current_user.first_name = request.form['first_name']
        current_user.last_name = request.form['last_name']
        current_user.job_title = request.form.get('job_title')
        current_user.company = request.form.get('company')

        try:
            db.session.commit()
            flash('Profile updated successfully.', 'success')
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred: {str(e)}', 'danger')
        return redirect(url_for('command_center.command_center'))  # Updated redirect to command center

    return render_template_string('''
        <h1>Edit Profile</h1>
        <form method="POST">
            <label for="first_name">First Name:</label><br>
            <input type="text" id="first_name" name="first_name" value="{{ current_user.first_name }}" required><br><br>
            <label for="last_name">Last Name:</label><br>
            <input type="text" id="last_name" name="last_name" value="{{ current_user.last_name }}" required><br><br>
            <label for="job_title">Job Title:</label><br>
            <input type="text" id="job_title" name="job_title" value="{{ current_user.job_title }}"><br><br>
            <label for="company">Company:</label><br>
            <input type="text" id="company" name="company" value="{{ current_user.company }}"><br><br>
            <input type="submit" value="Update Profile">
        </form>
    ''')

