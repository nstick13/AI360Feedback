from flask import Blueprint, render_template_string, redirect, url_for

# Define Blueprint for home
home_bp = Blueprint('home', __name__)

# Home Page Route
@home_bp.route('/home')
def home():
    return render_template_string('''
        <h1>FSO Feedback App</h1>
        <p>Welcome to the Foreign Service Officer Feedback App!</p>
        <a href="{{ url_for('auth.signup') }}">Sign Up</a><br>
        <a href="{{ url_for('auth.login') }}">Log In</a>
    ''')

# Redirect from '/' to '/home'
@home_bp.route('/')
def index():
    return redirect(url_for('home.home'))
