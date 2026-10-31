@echo off
cd /d "%~dp0"
echo Plakzicht Mail wordt gestart...
python -m pip install --quiet --disable-pip-version-check -r requirements-desktop.txt
python app.py
if errorlevel 1 pause
