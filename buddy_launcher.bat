@echo off

ECHO Starting Python application...
:: This starts your Python app in a new command window.
:: The "cmd /k" part will keep the window open even if the Python script
:: crashes or finishes. This is useful for seeing error messages.
start "Python App" cmd /k "python core/base_app.py"

ECHO Launching HTML interface...
:: This opens the index.html file in your default web browser.
:: "start" without a title will use the file's default program.
start index.html

ECHO Done.

