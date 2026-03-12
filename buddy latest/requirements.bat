@echo off
ECHO Installing all required Python libraries...
ECHO This may take a few minutes.
ECHO.

:: Using python -m pip to ensure we use the correct Python executable
python -m pip install flask
python -m pip install flask-cors
python -m pip install requests
python -m pip install textblob
python -m pip install vosk
python -m pip install sounddevice
python -m pip install edge-tts
python -m pip install pygame
python -m pip install numpy

ECHO.
ECHO All required libraries have been installed (or updated).
ECHO.
ECHO Press any key to close this window.
pause
