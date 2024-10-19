from flask import Flask, request, session, jsonify, render_template_string, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from flask_mail import Mail, Message
import openai
import os
from itsdangerous import URLSafeTimedSerializer

# Initialize the Flask app
app = Flask(__name__)
app.secret_key = 'supersecretkey'  # For session management
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///users.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
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
    email = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(150), nullable=False)

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
        db.session.commit()

        # Send verification email
        token = generate_verification_token(email)
        verify_url = url_for('verify_email', token=token, _external=True)
        msg = Message('Please verify your email', sender='noreply@example.com', recipients=[email])
        msg.body = f'Click the link to verify your email: {verify_url}'
        mail.send(msg)

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
            return redirect(url_for('home'))

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

@app.route('/', methods=['GET', 'POST'])
@login_required
def home():
    # Initialize conversation history if not present
    if 'conversation' not in session:
        session['conversation'] = [
            {"role": "system", "content": (
                "You're having a casual conversation with a colleague at a coffee shop. "
                "Your goal is to gather feedback on a Foreign Service Officer (FSO). Keep the conversation light and focused."
            )}
        ]

    if request.method == 'POST':
        # Get the user's message from the AJAX request
        user_input = request.form['message']

        # Append the user message to the conversation history
        conversation = session.get('conversation', [])
        conversation.append({"role": "user", "content": user_input})

        # Generate AI response
        ai_response = generate_ai_response(conversation)

        # Append AI response to conversation history
        conversation.append({"role": "assistant", "content": ai_response})

        # Save updated conversation back to the session
        session['conversation'] = conversation

        # Return the AI response as JSON (for AJAX)
        return jsonify({'ai_response': ai_response})

    # If the request is GET, return the HTML template
    return render_template_string('''
        <h1>Feedback Conversation</h1>
        <div id="conversation">
            {% for message in session['conversation'][1:] %}
                <p><strong>{{ message.role }}:</strong> {{ message.content }}</p>
            {% endfor %}
        </div>

        <form id="chatForm">
            <label for="message">Your message:</label><br>
            <input type="text" id="message" name="message" autofocus><br><br>
            <input type="submit" value="Send">
            <button id="newConversation">Start New Conversation</button>
        </form>
        <a href="{{ url_for('logout') }}">Logout</a>

        <script src="https://code.jquery.com/jquery-3.6.0.min.js"></script>
        <script>
            $(document).ready(function() {
                $('#chatForm').on('submit', function(e) {
                    e.preventDefault(); // Prevent page reload

                    var userMessage = $('#message').val(); // Get the message from the input

                    // Send the message via AJAX
                    $.ajax({
                        type: 'POST',
                        url: '/',
                        data: { message: userMessage },
                        success: function(response) {
                            // Append the user message and AI response to the conversation
                            $('#conversation').append('<p><strong>user:</strong> ' + userMessage + '</p>');
                            $('#conversation').append('<p><strong>assistant:</strong> ' + response.ai_response + '</p>');

                            // Clear the input field
                            $('#message').val('');
                        }
                    });
                });

                $('#newConversation').on('click', function(e) {
                    e.preventDefault(); // Prevent page reload

                    // Clear the session conversation via AJAX
                    $.ajax({
                        type: 'POST',
                        url: '/new_conversation',
                        success: function() {
                            // Clear the conversation div
                            $('#conversation').html('');
                        }
                    });
                });
            });
        </script>
    ''')

@app.route('/new_conversation', methods=['POST'])
def new_conversation():
    # Clear the conversation history
    session.pop('conversation', None)
    return '', 204

def generate_ai_response(conversation_history):
    try:
        # Send the conversation to OpenAI API
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=conversation_history,
            temperature=0.7,
            max_completion_tokens=150
        )
        # Access the assistant's message content
        return response.choices[0].message.content
    except Exception as e:
        return f"An error occurred: {e}"

if __name__ == "__main__":
    with app.app_context():
        db.create_all()  # Create tables if not exist
    app.run(host='0.0.0.0', port=8080)
