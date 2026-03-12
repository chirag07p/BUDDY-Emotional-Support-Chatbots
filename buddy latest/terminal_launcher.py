import sys
import os
import threading
import time
from core import *

class TerminalBuddyLauncher:
    """Terminal-based launcher for all Buddy modes"""
    
    def __init__(self):
        self.current_mode = None
        self.current_session = None
        
        print("="*60)
        print("💝 BUDDY - Your Caring AI Companion")
        print("🎤 Realistic Female Voice | 🧠 Emotional Intelligence")
        print("="*60)
        
    def show_main_menu(self):
        """Display main menu and handle selection"""
        while True:
            print("\n" + "="*40)
            print("🌟 CHOOSE YOUR SESSION MODE:")
            print("="*40)
            print("1. 💾 Regular Session")
            print("   • Conversations saved for continuity")
            print("   • Session history and summaries")
            print("   • Follow-up questions from previous sessions")
            print("   • Long-term emotional tracking")
            print()
            print("2. 🎤 Hands-Free Mode")
            print("   • Continuous voice interaction")
            print("   • No typing required")
            print("   • Natural conversation flow")
            print("   • Perfect for accessibility")
            print()
            print("3. 🔒 Private Session")
            print("   • Nothing saved or stored")
            print("   • Complete privacy and confidentiality")
            print("   • No login required")
            print("   • Data deleted on exit")
            print()
            print("4. ❌ Exit")
            print("="*40)
            
            try:
                choice = input("\nEnter your choice (1-4): ").strip()
                
                if choice == "1":
                    self.start_regular_session()
                elif choice == "2":
                    self.start_hands_free_session()
                elif choice == "3":
                    self.start_private_session()
                elif choice == "4":
                    print("\n💕 Goodbye! Take care of yourself!")
                    break
                else:
                    print("❌ Invalid choice. Please enter 1-4.")
                    
            except KeyboardInterrupt:
                print("\n\n💕 Goodbye! Take care of yourself!")
                break
            except Exception as e:
                print(f"❌ Error: {e}")
    
    def start_regular_session(self):
        """Start regular session mode"""
        print("\n💾 Starting Regular Session Mode...")
        
        try:
            session = RegularTerminalSession()
            session.run()
        except Exception as e:
            print(f"❌ Error starting regular session: {e}")
            input("Press Enter to continue...")
    
    def start_hands_free_session(self):
        """Start hands-free session mode"""
        print("\n🎤 Starting Hands-Free Mode...")
        
        try:
            session = HandsFreeTerminalSession()
            session.run()
        except Exception as e:
            print(f"❌ Error starting hands-free session: {e}")
            input("Press Enter to continue...")
    
    def start_private_session(self):
        """Start private session mode"""
        print("\n🔒 Starting Private Session Mode...")
        
        # Show privacy notice
        privacy_notice = """
🔒 PRIVATE SESSION MODE

This is a completely private and confidential chat session:

1. NO conversations will be saved or stored
2. NO data will be persistent after you exit
3. NO session history or summaries will be created
4. Complete privacy and confidentiality guaranteed
5. Non-judgmental emotional support only

Your privacy is our priority. This is a safe space for 
you to express yourself freely.
        """
        
        print(privacy_notice)
        consent = input("\nDo you want to continue with Private Session Mode? (y/n): ").strip().lower()
        
        if consent in ['y', 'yes']:
            try:
                session = PrivateTerminalSession()
                session.run()
            except Exception as e:
                print(f"❌ Error starting private session: {e}")
                input("Press Enter to continue...")
        else:
            print("Private session cancelled.")
            input("Press Enter to continue...")

class RegularTerminalSession:
    """Regular session with full features"""
    
    def __init__(self):
        self.db = SQLiteDB()
        self.analyzer = EmotionAnalyzer()
        self.prompt_generator = FemaleSupportivePromptGenerator(self.analyzer)
        self.router_api = OpenRouterAPI()
        self.session_manager = SessionManager(self.db)
        self.speech_handler = HumanLikeSpeechHandler()
        self.user_name = None
        
    def run(self):
        """Run regular session"""
        if not self.login():
            return
        
        self.session_manager.start_new_session(self.user_name)
        
        print(f"\n✨ Welcome {self.user_name}! Starting your regular session...")
        
        # Check for session context
        session_context = self.session_manager.get_session_context(self.user_name)
        if session_context:
            self.show_session_welcome(session_context)
        else:
            welcome_msg = f"Hi {self.user_name}! How are you feeling today? I'm here to listen and support you. 💕"
            self.show_message("Buddy", welcome_msg)
            self.speech_handler.speak(welcome_msg)
        
        self.chat_loop()
    
    def login(self):
        """Simplified login - just get name"""
        while True:
            try:
                name = input("\n💬 What's your name, dear? ").strip()
                if not name:
                    print("😊 I'd love to know your name so I can address you personally.")
                    continue
                
                self.user_name = name
                print(f"✨ Welcome {name}!")
                return True
                        
            except KeyboardInterrupt:
                return False
    
    def show_session_welcome(self, session_context):
        """Show welcome with session context"""
        latest_session = session_context[0]
        
        welcome_msg = f"Welcome back, {self.user_name}! I remember our conversation from {latest_session['session_date']}. 😊"
        
        if latest_session['summary']:
            welcome_msg += f"\n\nLast time we talked about: {latest_session['summary']}"
        
        if latest_session['follow_up_questions']:
            questions = latest_session['follow_up_questions'].split(" | ")
            welcome_msg += f"\n\nI've been wondering:"
            for i, question in enumerate(questions[:2], 1):
                welcome_msg += f"\n{i}. {question}"
            welcome_msg += f"\n\nHow have you been, {self.user_name}?"
        
        self.show_message("Buddy", welcome_msg)
        self.speech_handler.speak(welcome_msg)
    
    def chat_loop(self):
        """Main chat loop"""
        print(f"\n{'='*50}")
        print(f"💬 Chat with Buddy")
        print(f"Commands: 'voice' (voice input), 'history' (show sessions), 'quit' (exit)")
        print(f"{'='*50}")
        
        while True:
            try:
                user_input = input(f"\n{self.user_name}: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    self.handle_goodbye()
                    break
                
                if user_input.lower() in ['voice', 'listen', 'talk']:
                    self.handle_voice_input()
                    continue
                
                if user_input.lower() in ['history', 'sessions']:
                    self.show_session_history()
                    continue
                
                self.process_user_input(user_input)
                
            except KeyboardInterrupt:
                print(f"\n\n💕 Goodbye {self.user_name}! Take care of yourself!")
                break
    
    def process_user_input(self, user_input):
        """Process user input and generate response"""
        self.db.insert_message(self.user_name, "User", user_input)
        
        # Analyze emotions
        user_analysis = self.analyzer.analyze(user_input)
        
        # Get context
        chat_history = self.db.get_last_messages(self.user_name)
        session_context = self.session_manager.get_session_context(self.user_name)
        
        # Generate response
        system_prompt, user_prompt = self.prompt_generator.create_prompt(
            user_input, user_analysis, chat_history, session_context, self.user_name
        )
        
        response = self.router_api.generate_response(system_prompt, user_prompt)
        
        # Save and display
        self.db.insert_message(self.user_name, "Buddy", response)
        self.show_message("Buddy", response)
        self.speech_handler.speak(response)
    
    def handle_voice_input(self):
        """Handle voice input"""
        print("\n🎤 I'm listening... Please speak now.")
        
        def on_voice_recognized(text):
            if text:
                print(f"\n🗣️  {self.user_name} (voice): {text}")
                self.process_user_input(text)
            else:
                print("❌ I couldn't hear you clearly, dear. Please try typing instead.")
        
        # Voice recognition in thread
        threading.Thread(
            target=lambda: self.speech_handler.listen(on_voice_recognized),
            daemon=True
        ).start()
    
    def show_session_history(self):
        """Show session history"""
        summaries = self.db.get_recent_session_summaries(self.user_name, limit=5)
        
        if not summaries:
            print(f"\n📖 No previous sessions found, {self.user_name}.")
            return
        
        print(f"\n📖 Your Recent Sessions, {self.user_name}:")
        print("="*50)
        
        for i, summary in enumerate(summaries, 1):
            print(f"\nSession {i} ({summary['created_at'][:10]}):")
            print(f"   Summary: {summary['summary']}")
            if summary['key_topics']:
                print(f"   Topics: {summary['key_topics']}")
    
    def show_message(self, sender, message):
        """Display message"""
        if sender == "Buddy":
            print(f"\n💝 Buddy: {message}")
        else:
            print(f"\n🗣️  {self.user_name}: {message}")
    
    def handle_goodbye(self):
        """Handle goodbye"""
        if self.session_manager.get_current_session_id():
            self.session_manager.end_session(self.user_name, self.analyzer)
        
        goodbye_msg = f"Take care, {self.user_name}! Remember that you're important and I'm always here when you need support. 💕"
        self.show_message("Buddy", goodbye_msg)
        self.speech_handler.speak(goodbye_msg)
        
        time.sleep(3)
        self.speech_handler.shutdown()

class HandsFreeTerminalSession:
    """Hands-free session with continuous voice"""
    
    def __init__(self):
        self.db = SQLiteDB()
        self.analyzer = EmotionAnalyzer()
        self.prompt_generator = FemaleSupportivePromptGenerator(self.analyzer)
        self.router_api = OpenRouterAPI()
        self.session_manager = SessionManager(self.db)
        self.speech_handler = HandsFreeSpeechHandler()
        self.user_name = None
        self.hands_free_active = False
        self.processing_speech = False
        
    def run(self):
        """Run hands-free session"""
        if not self.login():
            return
        
        self.session_manager.start_new_session(self.user_name)
        
        print(f"\n🎤 Welcome to Hands-Free Mode, {self.user_name}!")
        print("This mode allows continuous voice interaction without typing.")
        
        welcome_msg = f"Hi {self.user_name}! I'm ready for hands-free conversation. Just start speaking when you're ready!"
        self.show_message("Buddy", welcome_msg)
        self.speech_handler.speak(welcome_msg)
        
        self.start_hands_free_mode()
    
    def login(self):
        """Simplified login - just get name"""
        while True:
            try:
                name = input("\n💬 What's your name for hands-free mode? ").strip()
                if not name:
                    print("😊 I'd love to know your name so I can address you personally.")
                    continue
                
                self.user_name = name
                print(f"✨ Welcome {name}!")
                return True
                        
            except KeyboardInterrupt:
                return False
    
    def start_hands_free_mode(self):
        """Start hands-free listening"""
        self.hands_free_active = True
        print(f"\n🎤 HANDS-FREE MODE ACTIVE")
        print(f"Speak naturally, {self.user_name} - I'm listening continuously!")
        print("Press Ctrl+C to exit hands-free mode")
        
        self.speech_handler.start_hands_free_mode(self.on_hands_free_speech)
        
        try:
            while self.hands_free_active:
                time.sleep(0.1)
        except KeyboardInterrupt:
            self.stop_hands_free_mode()
    
    def on_hands_free_speech(self, text):
        """Handle hands-free speech input"""
        if text and self.hands_free_active and not self.processing_speech:
            self.processing_speech = True
            print(f"\n🗣️  {self.user_name}: {text}")
            
            # Check for exit commands
            if any(cmd in text.lower() for cmd in ['goodbye', 'exit', 'stop listening', 'quit']):
                self.handle_goodbye()
                return
            
            self.process_hands_free_input(text)
    
    def process_hands_free_input(self, text):
        """Process hands-free input"""
        self.db.insert_message(self.user_name, "User", text)
        
        # Pause listening during processing
        self.speech_handler.pause_listening()
        
        # Generate response
        user_analysis = self.analyzer.analyze(text)
        chat_history = self.db.get_last_messages(self.user_name)
        
        system_prompt, user_prompt = self.prompt_generator.create_prompt(
            text, user_analysis, chat_history, None, self.user_name
        )
        
        response = self.router_api.generate_response(system_prompt, user_prompt)
        
        # Save and speak response
        self.db.insert_message(self.user_name, "Buddy", response)
        self.show_message("Buddy", response)
        
        # Speak with callback to resume listening
        self.speech_handler.speak(response, self.on_tts_complete)
    
    def on_tts_complete(self):
        """Called when TTS completes"""
        if self.hands_free_active:
            # Resume listening after delay
            time.sleep(1)
            self.speech_handler.resume_listening()
            self.processing_speech = False
            print(f"🎤 Listening for {self.user_name}...")
    
    def stop_hands_free_mode(self):
        """Stop hands-free mode"""
        self.hands_free_active = False
        self.speech_handler.stop_hands_free_mode()
        print("\n🎤 Hands-free mode stopped")
    
    def show_message(self, sender, message):
        """Display message"""
        if sender == "Buddy":
            print(f"\n💝 Buddy: {message}")
        else:
            print(f"\n🗣️  {self.user_name}: {message}")
    
    def handle_goodbye(self):
        """Handle goodbye"""
        self.stop_hands_free_mode()
        
        goodbye_msg = f"Goodbye {self.user_name}! It was wonderful talking with you hands-free!"
        self.show_message("Buddy", goodbye_msg)
        self.speech_handler.speak(goodbye_msg)
        
        time.sleep(3)
        self.speech_handler.shutdown()

class PrivateTerminalSession:
    """Private session with no data persistence"""
    
    def __init__(self):
        self.db = PrivateSessionDB()
        self.analyzer = PrivateEmotionAnalyzer()
        self.prompt_generator = PrivatePromptGenerator(self.analyzer)
        self.router_api = OpenRouterAPI()
        self.speech_handler = HumanLikeSpeechHandler()
        self.user_name = f"Anonymous_{int(time.time())}"
        
    def run(self):
        """Run private session"""
        print(f"\n🔒 Starting Private Session - No Data Saved")
        
        welcome_msg = """Welcome to your private session! 🔒

This is a completely confidential space where:
• Nothing is saved or stored
• You can speak freely without judgment
• Your privacy is absolutely guaranteed

How are you feeling today? I'm here to listen and support you."""
        
        self.show_message("Buddy", welcome_msg)
        self.speech_handler.speak(welcome_msg)
        
        self.chat_loop()
    
    def chat_loop(self):
        """Private chat loop"""
        print(f"\n{'='*50}")
        print(f"🔒 Private Chat Mode - Nothing Saved")
        print(f"Commands: 'voice' (voice input), 'quit' (exit)")
        print(f"{'='*50}")
        
        while True:
            try:
                user_input = input(f"\nYou: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ['quit', 'exit', 'bye']:
                    self.handle_goodbye()
                    break
                
                if user_input.lower() in ['voice', 'listen', 'talk']:
                    self.handle_voice_input()
                    continue
                
                self.process_user_input(user_input)
                
            except KeyboardInterrupt:
                print(f"\n\n🔒 Private session ended - all data cleared!")
                break
    
    def process_user_input(self, user_input):
        """Process private user input"""
        self.db.add_message("User", user_input)
        
        # Analyze and generate response
        user_analysis = self.analyzer.analyze(user_input)
        chat_history = self.db.get_recent_messages()
        
        system_prompt, user_prompt = self.prompt_generator.create_prompt(
            user_input, user_analysis, chat_history, None, "friend"
        )
        
        response = self.router_api.generate_response(system_prompt, user_prompt)
        
        # Add privacy reminder occasionally
        if len(response) > 50 and "private" not in response.lower():
            if len(self.db.session_messages) % 5 == 0:  # Every 5th message
                response += "\n\n🔒 Remember: This conversation is completely private and confidential."
        
        self.db.add_message("Buddy", response)
        self.show_message("Buddy", response)
        self.speech_handler.speak(response)
    
    def handle_voice_input(self):
        """Handle voice input in private mode"""
        print("\n🎤 I'm listening privately... (nothing recorded)")
        
        def on_voice_recognized(text):
            if text:
                print(f"\n🗣️  You (voice): {text}")
                self.process_user_input(text)
            else:
                print("❌ Please try again or type your message.")
        
        threading.Thread(
            target=lambda: self.speech_handler.listen(on_voice_recognized),
            daemon=True
        ).start()
    
    def show_message(self, sender, message):
        """Display message in private mode"""
        if sender == "Buddy":
            print(f"\n💝 Buddy: {message}")
        else:
            print(f"\n🗣️  You: {message}")
    
    def handle_goodbye(self):
        """Handle private session goodbye"""
        print("\n🔒 Clearing all session data...")
        self.db.clear_session()
        
        goodbye_msg = "Take care! Remember, our entire conversation has been completely private. ✅ All data cleared."
        self.show_message("Buddy", goodbye_msg)
        self.speech_handler.speak(goodbye_msg)
        
        time.sleep(3)
        self.speech_handler.shutdown()

def main():
    """Main entry point"""
    try:
        launcher = TerminalBuddyLauncher()
        launcher.show_main_menu()
    except KeyboardInterrupt:
        print("\n\n💕 Goodbye! Take care of yourself!")
    except Exception as e:
        print(f"❌ Fatal error: {e}")

if __name__ == "__main__":
    main()
