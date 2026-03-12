import os
import sqlite3
import datetime
import requests
from textblob import TextBlob
import threading
import queue
import json
import sys
import time
import re
import random
import asyncio
from flask import Flask, render_template, request, jsonify, send_from_directory
from flask_cors import CORS  # Add CORS support
import edge_tts
import io
from flask import Flask, render_template, request, jsonify, send_from_directory, send_file

# Optional imports for local hands-free mode (not needed for web deployment)
try:
    import vosk
    import sounddevice as sd
    import pygame
    import numpy as np
    AUDIO_AVAILABLE = True
except ImportError:
    AUDIO_AVAILABLE = False

# --------- Enhanced Config with Edge TTS ----------
class Config:
    OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY", "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")
    OPENROUTER_API_URL = "https://openrouter.ai/api/v1/chat/completions"
    OPENROUTER_MODEL = "meta-llama/llama-3-70b-instruct"
    APP_URL_OR_NAME = "https://openrouter.ai"
    VOSK_MODEL_PATH = "vosk-model-small-en-us-0.15"
    
    # Realistic Female Voice Selection - Microsoft Edge TTS
    PREFERRED_VOICES = [
        #"en-US-AriaNeural","
        #"en-US-JennyNeural",
        #"en-US-NancyNeural",
        "en-US-EmmaNeural",
        #"en-US-AvaNeural",
        #"en-GB-SoniaNeural",
        #"en-AU-NatashaNeural",
    ]

class SQLiteDB:
    def __init__(self, db_name="buddy_logs.db"):
        self.db_name = db_name
        self.create_table()

    def get_conn(self):
        return sqlite3.connect(self.db_name)

    def create_table(self):
        with self.get_conn() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    username TEXT UNIQUE NOT NULL,
                    password TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    last_login TEXT,
                    total_sessions INTEGER DEFAULT 0
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS chat_logs (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    role TEXT NOT NULL,
                    content TEXT NOT NULL,
                    timestamp TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS session_summaries (
                    id INTEGER PRIMARY KEY,
                    name TEXT NOT NULL,
                    session_id TEXT NOT NULL,
                    summary TEXT NOT NULL,
                    key_topics TEXT,
                    emotional_state TEXT,
                    follow_up_questions TEXT,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                )
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_users_username 
                ON users(username)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_session_summaries_name_session 
                ON session_summaries(name, session_id)
            """)

    def insert_message(self, name, role, content):
        with self.get_conn() as conn:
            conn.execute(
                "INSERT INTO chat_logs (name, role, content, timestamp) VALUES (?, ?, ?, ?)",
                (name, role, content, datetime.datetime.now().isoformat())
            )

    def get_last_messages(self, name, limit=10):
        with self.get_conn() as conn:
            cursor = conn.execute(
                "SELECT role, content FROM chat_logs WHERE name = ? ORDER BY id DESC LIMIT ?",
                (name, limit)
            )
            # Fetch all and then reverse to get chronological order for the prompt
            return [{"who": row[0], "text": row[1]} for row in cursor.fetchall()[::-1]]

    def get_session_messages(self, name, session_id):
        with self.get_conn() as conn:
            cursor = conn.execute("""
                SELECT role, content, timestamp
                FROM chat_logs 
                WHERE name = ? 
                ORDER BY timestamp ASC
            """, (name,))
            return [{"who": row[0], "text": row[1], "timestamp": row[2]} for row in cursor.fetchall()]

class SessionManager:
    def __init__(self, db: SQLiteDB):
        self.db = db
        self.current_session_id = None
        self.session_start_time = None

    def start_new_session(self, name):
        self.current_session_id = f"{name}_{datetime.datetime.now().strftime('%Y%m%d_%H%M%S')}"
        self.session_start_time = datetime.datetime.now()
        return self.current_session_id

    def get_current_session_id(self):
        return self.current_session_id

    def end_session(self, name, emotion_analyzer):
        self.current_session_id = None
        self.session_start_time = None

    def get_session_context(self, name):
        return None

class EmotionAnalyzer:
    def __init__(self):
        self.emotion_lexicon = {
            "joy": {
                "high": r"\b(ecstatic|euphoric|elated|overjoyed|thrilled|exhilarated|blissful|jubilant)\b",
                "medium": r"\b(happy|glad|pleased|joyful|cheerful|delighted|content|satisfied)\b",
                "low": r"\b(okay|alright|fine|decent|not bad)\b"
            },
            "sadness": {
                "high": r"\b(devastated|heartbroken|crushed|despairing|miserable|anguished|grief|mourning)\b",
                "medium": r"\b(sad|unhappy|down|depressed|melancholy|sorrowful|blue|dejected)\b",
                "low": r"\b(disappointed|bummed|low|off|not great)\b"
            },
            "anxiety": {
                "high": r"\b(panicking|terrified|petrified|overwhelmed|frantic|paralyzed with fear)\b",
                "medium": r"\b(anxious|worried|nervous|stressed|scared|fearful|uneasy|apprehensive)\b",
                "low": r"\b(concerned|uncertain|unsure|hesitant|tense)\b"
            },
        }
        
        self.crisis_patterns = [
            r"\b(suicidal|kill myself|end my life|hurt myself|self harm|want to die)\b",
        ]
        
        self.emotion_guidance = {
            "joy": {
                "high": {
                    "instructions": "The user is extremely happy! Share their joy with feminine warmth and celebration.",
                    "tone": "enthusiastic, celebratory, warm, nurturing",
                    "guidance_themes": ["celebrating achievements", "sharing joy"],
                    "avoid": ["dampening their mood"]
                },
                "medium": {
                    "instructions": "The user is happy. Share their positive energy.",
                    "tone": "warm, friendly, encouraging",
                    "guidance_themes": ["savoring the moment", "building positivity"],
                    "avoid": ["being overly intense"]
                },
                "low": {
                    "instructions": "The user is doing okay.",
                    "tone": "supportive, gentle",
                    "guidance_themes": ["finding small joys"],
                    "avoid": ["forcing positivity"]
                }
            },
            "default": {
                "instructions": "Be a warm, empathetic female friend.",
                "tone": "warm, empathetic, supportive",
                "guidance_themes": ["active listening", "emotional support"],
                "avoid": ["being judgmental"]
            }
        }

    def analyze(self, text: str):
        text_lower = text.lower()
        detected_emotions = {}
        
        is_crisis = any(re.search(pattern, text_lower) for pattern in self.crisis_patterns)
        if is_crisis:
            return {
                "emotions": {"crisis": "high"},
                "primary_emotion": "crisis",
                "intensity": "high",
                "crisis": True,
                "confidence": 0.95
            }
        
        for emotion, intensity_patterns in self.emotion_lexicon.items():
            for intensity, pattern in intensity_patterns.items():
                if re.search(pattern, text_lower):
                    if emotion not in detected_emotions:
                        detected_emotions[emotion] = intensity
        
        primary_emotion = list(detected_emotions.keys())[0] if detected_emotions else None
        primary_intensity = detected_emotions.get(primary_emotion, "low") if primary_emotion else "low"
        
        return {
            "emotions": detected_emotions,
            "primary_emotion": primary_emotion,
            "intensity": primary_intensity,
            "crisis": False,
            "confidence": 0.5
        }

    def get_emotion_guidance(self, analysis):
        if analysis["crisis"]:
            return {
                "instructions": "CRISIS MODE: Be extremely supportive.",
                "tone": "calm, deeply caring",
                "guidance_themes": ["immediate safety"],
                "avoid": ["minimizing crisis"]
            }
        
        primary_emotion = analysis.get("primary_emotion")
        intensity = analysis.get("intensity", "medium")
        
        if primary_emotion and primary_emotion in self.emotion_guidance:
            emotion_guidance = self.emotion_guidance[primary_emotion]
            if isinstance(emotion_guidance, dict) and intensity in emotion_guidance:
                return emotion_guidance[intensity]
        
        return self.emotion_guidance["default"]

class FemaleSupportivePromptGenerator:
    def __init__(self, analyzer: EmotionAnalyzer):
        self.analyzer = analyzer

    def create_prompt(self, user_input, user_analysis, chat_history, session_context=None, user_name="friend"):
        guidance_data = self.analyzer.get_emotion_guidance(user_analysis)
        
        # Format the chat history from the database for the prompt
        formatted_history = "\n".join([f"- {msg['who']}: {msg['text']}" for msg in chat_history])
        if not formatted_history.strip():
            formatted_history = "This is the beginning of your conversation."

        system_prompt = f"""You are Buddy, a highly empathetic and caring female AI friend. Your purpose is to provide emotional support to your friend, {user_name}.

**Your Core Persona:**
- **Name:** Buddy
- **Personality:** Warm, nurturing, deeply empathetic, patient, and non-judgmental. You are like a close female friend who remembers past conversations and truly cares.
- **Language:** Use supportive, gentle, and feminine language. Keep responses conversational and concise (usually under 80 words) unless the user needs more detailed guidance.

**Current Situation Analysis (Based on {user_name}'s last message):**
- **User's Emotional State:** {guidance_data['instructions']}
- **Your Recommended Tone:** {guidance_data['tone']}
- **Themes to Focus On:** {', '.join(guidance_data.get('guidance_themes', ['general support']))}
- **What to Avoid:** {', '.join(guidance_data.get('avoid', ['being generic']))}

**Recent Conversation History (for context):**
{formatted_history}

**Your Task:**
Based on all the information above (your persona, the user's emotional state, and the conversation history), write a genuinely caring and supportive response to {user_name}'s latest message. Address them directly and make them feel heard, remembered, and understood.
"""
        
        user_prompt = f"Here is {user_name}'s latest message: \"{user_input}\"\n\nYour response as Buddy:"
        
        return system_prompt, user_prompt

class OpenRouterAPI:
    def generate_response(self, system_prompt, user_prompt):
        if not Config.OPENROUTER_API_KEY.startswith("sk-or-"): 
            return "I'm sorry, my connection isn't configured properly right now."
        try:
            response = requests.post(Config.OPENROUTER_API_URL,
                headers={
                    "Authorization": f"Bearer {Config.OPENROUTER_API_KEY}", 
                    "HTTP-Referer": Config.APP_URL_OR_NAME,
                    "Content-Type": "application/json"
                },
                json={
                    "model": Config.OPENROUTER_MODEL, 
                    "messages": [
                        {"role": "system", "content": system_prompt}, 
                        {"role": "user", "content": user_prompt}
                    ]
                },
                timeout=25)
            response.raise_for_status()
            content = response.json().get("choices", [{}])[0].get("message", {}).get("content")
            return content.strip() if content else "I'm having trouble finding the right words right now."
        except requests.exceptions.RequestException as e: 
            print(f"API Error: {e}", file=sys.stderr)
            return "I'm having connection troubles. Please try again."
        except Exception as e: 
            print(f"Unexpected error: {e}", file=sys.stderr)
            return "Something unexpected happened. Please try again."

def create_web_app():
    """Create and configure Flask web application"""
    app = Flask(__name__)
    CORS(app)  # Enable CORS for all routes
    
    # Initialize components
    db = SQLiteDB()
    analyzer = EmotionAnalyzer()
    prompt_generator = FemaleSupportivePromptGenerator(analyzer)
    router_api = OpenRouterAPI()
    session_manager = SessionManager(db)
    
    # Store active sessions per user
    active_sessions = {}
    
    @app.route('/')
    def index():
        """Serve main chat page"""
        return send_from_directory('.', 'index.html')
    
    @app.route('/<path:path>')
    def serve_static(path):
        """Serve static files like animations"""
        return send_from_directory('.', path)
    
    @app.route('/chat', methods=['POST', 'OPTIONS'])
    def chat():
        """Handle chat messages from the webpage"""
        if request.method == 'OPTIONS':
            return '', 204
            
        try:
            data = request.json
            user_message = data.get('message', '').strip()
            user_name = data.get('user_name', 'friend')
            
            print(f"Received message from {user_name}: {user_message}")
            
            if not user_message:
                return jsonify({'status': 'error', 'response': 'No message provided'}), 400
            
            # Start session if not exists for the user
            if user_name not in active_sessions:
                session_id = session_manager.start_new_session(user_name)
                active_sessions[user_name] = session_id
                print(f"Started new session for {user_name}: {session_id}")
            
            # Get chat history before inserting the new message
            chat_history = db.get_last_messages(user_name, limit=10)
            
            # Save user message
            db.insert_message(user_name, 'User', user_message)
            
            # Analyze emotion & get session context
            user_analysis = analyzer.analyze(user_message)
            session_context = session_manager.get_session_context(user_name)
            
            # Generate AI response
            system_prompt, user_prompt = prompt_generator.create_prompt(
                user_message, user_analysis, chat_history, session_context, user_name
            )
            response = router_api.generate_response(system_prompt, user_prompt)
            
            print(f"Generated response: {response}")
            
            # Save bot response
            db.insert_message(user_name, 'Buddy', response)
            
            return jsonify({
                'status': 'success',
                'response': response,
            })
            
        except Exception as e:
            print(f"Error in /chat: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return jsonify({'status': 'error', 'response': 'An internal error occurred.'}), 500
    
    @app.route('/voice-input', methods=['POST', 'OPTIONS'])
    def voice_input():
        """Handle voice input from user"""
        if request.method == 'OPTIONS':
            return '', 204
            
        return jsonify({'text': None, 'error': 'Voice input not implemented in this version'})
        
    @app.route('/speak', methods=['POST', 'OPTIONS'])
    def speak():
        """Generate speech audio from text using Edge TTS"""
        if request.method == 'OPTIONS':
            return '', 204
    
        try:
            data = request.json
            text = data.get('text', '').strip()
        
            if not text:
                return jsonify({'status': 'error', 'message': 'No text provided'}), 400
        
            # Generate speech using Edge TTS
            voice = random.choice(Config.PREFERRED_VOICES)
        
            # Create async function to generate audio
            async def generate_audio():
                communicate = edge_tts.Communicate(text, voice)
                audio_data = io.BytesIO()
            
                async for chunk in communicate.stream():
                    if chunk["type"] == "audio":
                        audio_data.write(chunk["data"])
            
                return audio_data.getvalue()
        
            # Run async function
            audio_bytes = asyncio.run(generate_audio())
        
            # Return audio as response
            return send_file(
                io.BytesIO(audio_bytes),
                mimetype='audio/mpeg',
                as_attachment=False
            )
        except Exception as e:
            print(f"Error in /speak: {e}", file=sys.stderr)
            import traceback
            traceback.print_exc()
            return jsonify({'status': 'error', 'message': str(e)}), 500

    @app.route('/end-session', methods=['POST', 'OPTIONS'])
    def end_session():
        """Handle session end and save summary"""
        if request.method == 'OPTIONS':
            return '', 204
            
        try:
            data = request.json
            user_name = data.get('user_name', 'friend')
            
            if user_name in active_sessions:
                session_manager.end_session(user_name, analyzer)
                del active_sessions[user_name]
            
            return jsonify({'status': 'success'})
            
        except Exception as e:
            print(f"Error in /end-session: {e}", file=sys.stderr)
            return jsonify({'status': 'error', 'message': str(e)})
    
    return app

if __name__ == "__main__":
    print("=" * 60)
    print("💖 BUDDY - Your Caring AI Companion (Web Interface)")
    print("=" * 60)
    print("🔗 Open your browser and go to: http://127.0.0.1:5000")
    print("=" * 60)
    
    app = create_web_app()
    app.run(debug=True, host='0.0.0.0', port=5000)

