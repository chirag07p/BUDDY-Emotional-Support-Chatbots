# Buddy - AI Mental Health Support Assistant

A supportive AI chatbot with voice capabilities designed to provide emotional support and companionship.

## Features

- 💬 Text-based chat interface
- 🎤 Hands-free voice interaction
- 🧘 Breathing exercises
- 🔒 Privacy-focused sessions
- 🎯 Multiple session modes (Normal, Private, Hands-free)

## Installation

### Prerequisites
- Python 3.8 or higher
- pip (Python package manager)

### Setup

1. **Clone the repository**
   ```bash
   git clone https://github.com/YOUR_USERNAME/buddy.git
   cd buddy
   ```

2. **Create a virtual environment**
   ```bash
   python -m venv .venv
   ```

3. **Activate the virtual environment**
   - Windows:
     ```bash
     .venv\Scripts\activate
     ```
   - Linux/Mac:
     ```bash
     source .venv/bin/activate
     ```

4. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

5. **Run the application**
   ```bash
   python server.py
   ```

6. **Open in browser**
   - Navigate to `http://localhost:5000`
   - Open `index.html` or any session page

## Usage

- **Normal Session**: Standard chat interface
- **Private Session**: No data logging
- **Hands-free Mode**: Voice-controlled interaction
- **Breathing Session**: Guided breathing exercises

## Configuration

The application uses OpenRouter API for AI responses. You can configure the API key in `core/base_app.py`.

## Project Structure

```
buddy/
├── core/              # Backend logic and AI components
├── audio/             # Audio files
├── animations/        # Animation assets
├── images/            # Image assets
├── buttons/           # UI button assets
├── *.html            # Frontend pages
├── style.css         # Styling
├── server.py         # Flask backend server
└── requirements.txt  # Python dependencies
```

## License

This project is open source and available for personal use.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
