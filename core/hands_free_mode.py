# --- Python Standard Libraries ---
import numpy as np
import time
import threading
import queue
import json
import sys # <-- Make sure sys is imported
import asyncio
import io
import random
import os 

# --- Path Fix for Relative Imports ---
# Add the project root (parent of 'core') to the Python path
# This fixes "ImportError: attempted relative import with no known parent package"
# when running this script directly.
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.dirname(script_dir)
if project_root not in sys.path:
    sys.path.insert(0, project_root)
# --- End of Path Fix ---

# --- Third-party Libraries ---
import vosk
import sounddevice as sd
from flask import Flask, jsonify, request, send_from_directory, send_file
from flask_sock import Sock
from flask_cors import CORS
import edge_tts # <-- Added this import to fix the error

# --- Import Components from base_app.py ---
# (Assuming base_app.py is in the same directory)
from core.base_app import ( # <-- Changed from relative to absolute
    Config,
    SQLiteDB,
    EmotionAnalyzer,
    FemaleSupportivePromptGenerator,
    OpenRouterAPI,
    SessionManager
)

# --- Hands-Free Specific Config ---
class HandsFreeConfig(Config):
    VOICE_THRESHOLD = 0.01
    SILENCE_DURATION = 2.0
    MIN_SPEECH_DURATION = 0.5
    HANDS_FREE_BUFFER_SIZE = 1600
    AUTO_LISTEN_DELAY = 1.0

# --- Hands-Free Speech Handler Class ---
class HandsFreeSpeechHandler:
    def __init__(self):
        print("Initializing Speech Handler...")
        # Vosk model initialization
        self.vosk_model = None
        if os.path.exists(Config.VOSK_MODEL_PATH): # <-- This now works
            self.vosk_model = vosk.Model(Config.VOSK_MODEL_PATH)
        else:
            print(f"Vosk model path not found: {Config.VOSK_MODEL_PATH}")

        self.hands_free_mode = False
        self.hands_free_thread = None
        self.hands_free_running = False
        self.hands_free_paused = False
        self.voice_threshold = HandsFreeConfig.VOICE_THRESHOLD
        self.silence_duration = HandsFreeConfig.SILENCE_DURATION
        self.min_speech_duration = HandsFreeConfig.MIN_SPEECH_DURATION
        self.audio_queue = queue.Queue()
        print("Speech Handler Initialized.")

    def start_hands_free_mode(self, callback_func):
        """Start continuous hands-free listening"""
        if self.hands_free_running:
            return False
            
        self.hands_free_mode = True
        self.hands_free_running = True
        self.hands_free_paused = False
        self.hands_free_thread = threading.Thread(
            target=self._hands_free_worker, 
            args=(callback_func,), 
            daemon=True
        )
        self.hands_free_thread.start()
        print("🎤 Hands-free mode started")
        return True
    
    def stop_hands_free_mode(self):
        """Stop continuous hands-free listening"""
        self.hands_free_running = False
        self.hands_free_mode = False
        self.hands_free_paused = False
        if self.hands_free_thread:
            self.hands_free_thread.join(timeout=1)
        print("🎤 Hands-free mode stopped")
        return True
    
    def pause_listening(self):
        print("Pausing listening...")
        self.hands_free_paused = True
    
    def resume_listening(self):
        print("Resuming listening...")
        self.hands_free_paused = False
    
    def _detect_voice_activity(self, audio_data):
        """Simple voice activity detection"""
        try:
            audio_array = np.frombuffer(audio_data, dtype=np.int16)
            rms_energy = np.sqrt(np.mean(audio_array.astype(float) ** 2))
            normalized_energy = rms_energy / 32768.0
            return normalized_energy > self.voice_threshold
        except Exception as e:
            print(f"❌ Voice activity detection error: {e}")
            return False
    
    def _audio_callback(self, indata, frames, time, status):
        """Process incoming audio data"""
        if status:
            print(f"Audio status: {status}", file=sys.stderr)
        try:
            self.audio_queue.put(bytes(indata))
        except Exception as e:
            print(f"❌ Audio callback error: {e}")

    def _hands_free_worker(self, callback_func):
        """Continuous listening worker"""
        if not self.vosk_model:
            print("❌ Voice recognition not available. Vosk model not loaded.")
            return
        
        recognizer = vosk.KaldiRecognizer(self.vosk_model, 16000)
        audio_buffer = []
        speech_detected = False
        silence_start = None
        speech_start = None
        
        try:
            with sd.RawInputStream(
                samplerate=16000, 
                blocksize=HandsFreeConfig.HANDS_FREE_BUFFER_SIZE,
                dtype='int16', 
                channels=1,
                callback=self._audio_callback
            ):
                
                while self.hands_free_running:
                    try:
                        if self.hands_free_paused:
                            time.sleep(0.1)
                            # Clear the queue while paused
                            while not self.audio_queue.empty():
                                try:
                                    self.audio_queue.get_nowait()
                                except queue.Empty:
                                    break
                            continue
                        
                        try:
                            audio_data = self.audio_queue.get(timeout=0.1)
                        except queue.Empty:
                            continue
                        
                        current_time = time.time()
                        has_voice = self._detect_voice_activity(audio_data)
                        
                        if has_voice:
                            if not speech_detected:
                                speech_detected = True
                                speech_start = current_time
                                audio_buffer = []
                                silence_start = None
                                print("🗣️ Speech detected...")
                            
                            audio_buffer.append(audio_data)
                            
                        else:
                            if speech_detected:
                                if silence_start is None:
                                    silence_start = current_time
                                elif current_time - silence_start >= self.silence_duration:
                                    if speech_start and current_time - speech_start >= self.min_speech_duration:
                                        self._process_accumulated_speech(
                                            audio_buffer, recognizer, callback_func
                                        )
                                    
                                    # Reset state
                                    speech_detected = False
                                    audio_buffer = []
                                    silence_start = None
                                    speech_start = None
                        
                    except Exception as e:
                        print(f"❌ Hands-free audio processing error: {e}")
                        continue
                        
        except Exception as e:
            print(f"❌ Hands-free mode error: {e}")
    
    def _process_accumulated_speech(self, audio_buffer, recognizer, callback_func):
        """Process accumulated audio for speech recognition"""
        try:
            print("🔄 Processing speech...")
            
            # Feed all buffered audio to recognizer
            for audio_chunk in audio_buffer:
                recognizer.AcceptWaveform(audio_chunk)
            
            # Get final result
            result = json.loads(recognizer.FinalResult())
            text = result.get("text", "").strip()

            if text:
                print(f"✅ Recognized: {text}")
                # Use the main thread to run the callback
                # This is safer for web contexts
                callback_func(text)
            else:
                print("⚠️  No text recognized")
                
        except Exception as e:
            print(f"❌ Speech processing error: {e}")

# --- Flask App Initialization ---
app = Flask(__name__)
CORS(app)  # Enable CORS for all routes
sock = Sock(app) # Initialize Flask-Sock

# --- Initialize Core Components (from base_app) ---
print("Initializing core components...")
db = SQLiteDB()
analyzer = EmotionAnalyzer()
prompt_generator = FemaleSupportivePromptGenerator(analyzer)
router_api = OpenRouterAPI()
session_manager = SessionManager(db)
active_sessions = {} # Track active sessions
print("Core components initialized.")

# --- HTTP Routes (Copied from base_app) ---

@app.route('/')
def index():
    """Serve the hands-free session page by default"""
    return send_from_directory('.', 'hands-free-session.html')

@app.route('/<path:path>')
def serve_static(path):
    """Serve static files (e.g., animations, other html files)"""
    return send_from_directory('.', path)

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
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/end-session', methods=['POST', 'OPTIONS'])
def end_session_route():
    """Handle session end and save summary"""
    if request.method == 'OPTIONS':
        return '', 204
    # This is less relevant for WebSocket, but good to keep
    return jsonify({'status': 'success'})

# --- WebSocket Route ---

@sock.route('/ws_hands_free')
def ws_hands_free(ws):
    """Handle WebSocket connection for hands-free mode"""
    print("WebSocket client connected.")
    handler = HandsFreeSpeechHandler()
    user_name = "friend" # Default

    def send_ws_message(msg_type, **kwargs):
        """Helper to send JSON messages to client."""
        try:
            ws.send(json.dumps({"type": msg_type, **kwargs}))
        except Exception as e:
            print(f"Error sending message: {e}")

    def on_speech_recognized(text):
        """This is the callback_func for the speech handler."""
        print(f"Speech recognized: {text}")
        
        # 1. Send user_speech and status_update
        send_ws_message("status_update", status="processing", text="Processing...")
        send_ws_message("user_speech", text=text)
        
        try:
            # --- This logic is copied from base_app's /chat endpoint ---
            # 2. Get history
            chat_history = db.get_last_messages(user_name, limit=10)
            
            # 3. Save user message
            db.insert_message(user_name, 'User', text)
            
            # 4. Analyze emotion & get context
            user_analysis = analyzer.analyze(text)
            session_context = session_manager.get_session_context(user_name)
            
            # 5. Generate AI response
            system_prompt, user_prompt = prompt_generator.create_prompt(
                text, user_analysis, chat_history, session_context, user_name
            )
            response = router_api.generate_response(system_prompt, user_prompt)
            
            print(f"Generated response: {response}")
            
            # 6. Save bot response
            db.insert_message(user_name, 'Buddy', response)
            
            # 7. Send buddy_response
            send_ws_message("buddy_response", text=response)
            # The HTML client will now call /speak, which will
            # send a 'pause_listening' message.

        except Exception as e:
            print(f"Error in speech processing: {e}", file=sys.stderr)
            send_ws_message("error", text=f"Error processing speech: {e}")
            # Resume listening even if there's an error
            send_ws_message("status_update", status="listening", text="Listening...")

    # --- WebSocket Message Loop ---
    try:
        while True:
            message_data = ws.receive()
            if message_data:
                message = json.loads(message_data)
                action = message.get('action')
                
                if action == 'join':
                    user_name = message.get('user_name', 'friend')
                    if user_name not in active_sessions:
                        session_id = session_manager.start_new_session(user_name)
                        active_sessions[user_name] = session_id
                    
                    # Start the handler *after* join
                    handler.start_hands_free_mode(on_speech_recognized)
                    send_ws_message("status_update", status="connected", text="Connected")

                elif action == 'pause_listening':
                    handler.pause_listening()
                
                elif action == 'resume_listening':
                    handler.resume_listening()
                    send_ws_message("status_update", status="listening", text="Listening...")

    except Exception as e:
        print(f"WebSocket connection closed or error: {e}")
    
    finally:
        # --- Cleanup ---
        print("Stopping hands-free mode for this client.")
        handler.stop_hands_free_mode()
        if user_name in active_sessions:
            print(f"Ending session for {user_name}")
            session_manager.end_session(user_name, analyzer)
            del active_sessions[user_name]
        print("WebSocket client disconnected.")

# --- Run the App ---
if __name__ == "__main__":
    if not os.path.exists(Config.VOSK_MODEL_PATH): # <-- This now works
        print("=" * 60)
        print(f"ERROR: Vosk model not found at '{Config.VOSK_MODEL_PATH}'")
        print("Please download the model and place it in the correct directory.")
        print("=" * 60)
        sys.exit(1)

    print("=" * 60)
    print("💖 BUDDY - Hands-Free Mode Server 💖")
    print("=" * 60)
    print("🔗 Open your browser and go to: http://127.0.0.1:5000")
    print("✨ (Run from parent directory with: python -m core.hands_free_mode)")
    print("=" * 60)
    
    # We need to use a threaded server for Flask-Sock
    # 'debug=True' can cause issues with threading,
    # 'allow_unsafe_werkzeug=True' is needed for modern Flask
    print("Starting server...")
    try:
        from waitress import serve
        serve(app, host='0.0.0.0', port=5000)
    except ImportError:
        print("Waitress not found, running with Flask development server.")
        print("WARNING: Flask dev server is not recommended for production.")
        app.run(host='0.0.0.0', port=5000, debug=False)


