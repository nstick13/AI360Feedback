from flask import Blueprint, render_template_string
from flask_login import login_required, current_user
from .models import Feedback

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/dashboard', methods=['GET'])
@login_required
def dashboard():
    # Display feedback for the user
    feedbacks = Feedback.query.filter_by(user_id=current_user.id).all()

    return render_template_string('''
    <h2>Your Feedback</h2>
    {% if feedbacks %}
    <ul>
      {% for feedback in feedbacks %}
        <li><strong>From {{ feedback.giver.email }}:</strong> {{ feedback.content }}</li>
      {% endfor %}
    </ul>
    {% else %}
    <p>No feedback available yet.</p>
    {% endif %}
    <a href="{{ url_for('auth.logout') }}">Logout</a>
    ''', feedbacks=feedbacks)
