from flask import Blueprint, Flask, request, session, render_template_string, flash, redirect, url_for
from .models import db, FeedbackGiver, Feedback
import openai
import os

# Initialize the Flask app
app = Flask(__name__)
app.secret_key = 'supersecretkey'  # For session management

feedback_bp = Blueprint('feedback', __name__)

# Define the feedback route
@feedback_bp.route('/feedback_page', methods=['GET', 'POST'])
def feedback_page():
    try:
        # Token retrieval and validation
        token = request.args.get('token')
        if not token:
            flash('Access token is required to view this page.', 'danger')
            return redirect(url_for('home.index'))

        feedback_giver = FeedbackGiver.query.filter_by(token=token).first()
        if not feedback_giver:
            flash('Invalid or expired token.', 'danger')
            return redirect(url_for('home.index'))

        if feedback_giver.completed:
            flash('Feedback has already been completed for this token.', 'warning')
            return redirect(url_for('home.index'))

        session['giver_id'] = feedback_giver.id

    except Exception as e:
        flash(f'Server Error: {str(e)}', 'danger')
        return render_template_string('<p>Server error occurred. Please try again later.</p>')

    # Handle POST requests
    if request.method == 'POST':
        user_message = request.form.get('message', '')
        conversation_history = session.get('conversation_history', [])

        if 'end_chat' in request.form:
            # Save the entire conversation and end chat
            conversation_text = "\n".join(f"{msg['role']}: {msg['content']}" for msg in conversation_history)
            new_feedback = Feedback(
                content=conversation_text,
                user_id=feedback_giver.user_id,
                giver_id=feedback_giver.id
            )
            db.session.add(new_feedback)

            try:
                db.session.commit()
                flash('Chat ended and feedback saved.', 'success')
            except Exception as e:
                db.session.rollback()
                flash(f'Error saving feedback: {str(e)}', 'danger')

            session.pop('conversation_history', None)
            return redirect(url_for('home.index'))  # Redirect after saving

        # Continue chat with AI
        conversation_history.append({'role': 'user', 'content': user_message})
        response = openai.chat.completions.create(
            model="gpt-4o",
            messages=[
                {"role": "system", "content": "You are an AI designed to help colleagues provide feedback on Foreign Service Officers (FSOs) in a relaxed, conversational style—like friends chatting over coffee or a beer. Your goal is to guide them through a story-driven feedback process, asking open-ended questions about leadership, communication, and handling challenges.Start by asking what the person providing feedback has worked on with the FSO. Encourage them to share specific examples, then follow up with thoughtful questions to dive deeper. Occasionally paraphrase or summarize their responses to show you're actively listening and understanding. Keep the conversation friendly and engaging, and after about 10 minutes, check in to see how they’re feeling, adjusting the pace if needed. As you wrap up, casually summarize the session, highlighting strengths, areas for growth, and suggest actionable next steps, inviting them to confirm or add to the summary."},
                *conversation_history
            ],
            temperature=0.7
        )
        ai_message = response.choices[0].message.content
        conversation_history.append({'role': 'assistant', 'content': ai_message})
        session['conversation_history'] = conversation_history

    # Display the chat and form
    return render_template_string('''
        <h1>Chat with AI</h1>
        <div id="chatbox">
            {% for msg in conversation_history %}
                <p><strong>{{ msg['role'].capitalize() }}:</strong> {{ msg['content'] }}</p>
            {% endfor %}
        </div>
        <form method="POST">
            <label for="message">Your message:</label><br>
            <textarea id="message" name="message" rows="4" cols="50" required></textarea><br><br>
            <input type="submit" name="send" value="Send">
            <input type="submit" name="end_chat" value="End Chat and Save">
        </form>
    ''', conversation_history=session.get('conversation_history', []))