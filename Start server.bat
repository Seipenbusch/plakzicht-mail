@echo off
cd /d "%~dp0"
title Plakzicht Mail server
echo Plakzicht Mail server wordt gestart...
python -m pip install --quiet --disable-pip-version-check -r requirements.txt
python app.py --server
pause
