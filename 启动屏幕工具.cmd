@echo off
cd /d "%~dp0"
python -X utf8 gui.py
if errorlevel 1 pause
