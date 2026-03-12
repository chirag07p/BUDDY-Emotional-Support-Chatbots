from flask import Flask, request, jsonify
from core.base_app import (
    SQLiteDB,
    EmotionAnalyzer,
    FemaleSupportivePromptGenerator,
    OpenRouterAPI,
    SessionManager
)

# --- Initialization ---
# Initialize the Flask app
app = Flask(__name__)

# Initialize all the necessary components from your base_app
# These will be shared across all user requests
db = SQLiteDB()
analyzer = EmotionAnalyzer()
prompt_generator = FemaleSupportivePromptGenerator(analyzer)
router_api = OpenRouterAPI()
session_manager = SessionManager(db)

# For simplicity, we'll use a fixed username for this session.
# A real app would have a proper login system.
USER_NAME = "friend" 
session_manager.start_new_session(USER_NAME)

print("="*50)
print("🚀 Buddy Backend Server is running!")
print("Open 'normal-session.html' in your browser to chat.")
print("="*50)

# --- API Endpoint ---
@app.route('/chat', methods=['POST'])
def handle_chat():
    """
    This function is called by the JavaScript on your web page.
    It receives the user's message and returns Buddy's dynamic reply.
    """
    # 1. Get the user's message from the incoming request
    data = request.get_json()
    user_input = data.get('message')

    if not user_input:
        return jsonify({'error': 'No message received'}), 400

    # 2. Process the input using your base_app logic
    try:
        # Save user message to the database
        db.insert_message(USER_NAME, "User", user_input)
        
        # Analyze emotions
        user_analysis = analyzer.analyze(user_input)
        
        # Get chat history and session context
        chat_history = db.get_last_messages(USER_NAME)
        session_context = session_manager.get_session_context(USER_NAME)
        
        # Create the dynamic prompt
        system_prompt, user_prompt = prompt_generator.create_prompt(
            user_input, user_analysis, chat_history, session_context, USER_NAME
        )
        
        # Generate the response from the AI model
        response_text = router_api.generate_response(system_prompt, user_prompt)
        
        # Save Buddy's response to the database
        db.insert_message(USER_NAME, "Buddy", response_text)

        # 3. Send the generated response back to the web page
        return jsonify({'reply': response_text})

    except Exception as e:
        print(f"❌ An error occurred: {e}")
        # Return a generic error message to the frontend
        return jsonify({'reply': 'I\'m having a little trouble connecting right now.'}), 500

# --- Run the Server ---
if __name__ == '__main__':
    # This makes the server accessible on your local machine at http://127.0.0.1:5000
    app.run(port=5000)