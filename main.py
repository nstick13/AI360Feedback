from flask import Flask, request, session, jsonify, render_template_string
import openai
import os

# Initialize the Flask app
app = Flask(__name__)
app.secret_key = 'supersecretkey'  # For session management

# OpenAI API key
openai.api_key = os.getenv('OPENAI_API_KEY')

@app.route('/', methods=['GET', 'POST'])
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
    app.run(host='0.0.0.0', port=8080)
