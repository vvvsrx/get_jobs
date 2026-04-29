@echo off
setlocal

cd /d "%~dp0\.."

if not exist "static\" (
    echo First run detected. Running setup...
    python scripts\setup.py
)

echo Starting GetJobs server...
python run.py
