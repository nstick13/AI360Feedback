# Define Blueprint for the command center
from flask import Blueprint, render_template_string, request, flash, redirect, url_for, current_app
from flask_login import login_required, current_user
from flask_mail import Message
from .models import Feedback, FeedbackGiver, db
import uuid

command_center_bp =Blueprint('command_center', __name__)

@command_center_bp.route('/', methods=['GET', 'POST'])
@login_required
def command_center():
    try:
        # Query the database for feedbacks related to the current user
        user_feedbacks = Feedback.query.filter_by(user_id=current_user.id).all()
    except Exception as e:
        # Handle database query errors
        flash('Error fetching feedbacks: {}'.format(str(e)), 'danger')
        user_feedbacks = []

    if request.method == 'POST':
        # Handle form submission to send email invitations
        emails = request.form.getlist('emails')
        mail = current_app.extensions.get('mail')

        for email in emails:
            try:
                token = str(uuid.uuid4())
                # Create a new FeedbackGiver entry
                new_feedback_giver = FeedbackGiver(user_id=current_user.id, email=email, token=token)
                db.session.add(new_feedback_giver)
                db.session.commit()

                # Create the corresponding Feedback entry
                new_feedback = Feedback(user_id=current_user.id, giver_id=new_feedback_giver.id, content="")
                db.session.add(new_feedback)
                db.session.commit()

                feedback_url = url_for('feedback.feedback_page', token=token, _external=True)
                msg = Message(
                    'Your Feedback Invitation',
                    recipients=[email],
                    body=f'''Hi there!

                            You have been invited to provide feedback. Please use the following link to submit your feedback:
                            {feedback_url}

                            Thanks,
                            The Feedback Team'''
                )
                mail.send(msg)
                flash(f'Invitation sent to {email}.', 'success')
            except Exception as e:
                db.session.rollback()  # Roll back on error to maintain consistency
                flash(f'Failed to process email to {email}: {str(e)}', 'danger')

        return redirect(url_for('command_center.command_center'))

    # Render existing feedbacks or form for sending invitations
    return render_template_string('''
        <h1>Command Center</h1>
        <h2>Welcome, {{ current_user.first_name }} {{ current_user.last_name }}</h2>
        <h3>Your Feedbacks</h3>
        {% if user_feedbacks %}
            <ul>
            {% for feedback in user_feedbacks %}
                <li>{{ feedback.content }}</li>
            {% endfor %}
            </ul>
        {% else %}
            <p>No feedbacks available.</p>
        {% endif %}
        <h3>Invite Feedback Providers</h3>
        <form method="POST">
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    <ul class=flashes>
                        {% for category, message in messages %}
                            <li class="{{ category }}">{{ message }}</li>
                        {% endfor %}
                    </ul>
                {% endif %}
            {% endwith %}
            <label for="emails">Enter email addresses:</label><br>
            <input type="email" name="emails" multiple><br><br>
            <input type="submit" value="Send Invitations">
        </form>
    ''', user_feedbacks=user_feedbacks)