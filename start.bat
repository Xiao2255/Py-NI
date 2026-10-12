@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
    echo Please follow README.md to install dependencies first.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" main.py
if errorlevel 1 pause
