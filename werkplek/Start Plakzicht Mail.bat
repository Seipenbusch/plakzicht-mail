@echo off
cd /d "%~dp0"
python -m pip install --quiet --disable-pip-version-check pywebview
start "" pythonw werkplek.py
