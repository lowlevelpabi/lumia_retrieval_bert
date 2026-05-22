@echo off
TITLE Smart Research Backend
echo Starting Smart Research Backend Server...
cd /d "%~dp0"

IF NOT EXIST "venv" (
    echo [ERROR] Virtual environment 'venv' not found.
    echo Please run './setup_local.ps1' in PowerShell first.
    pause
    exit /b
)

echo Activating virtual environment...
call venv\Scripts\activate

echo Launching FastAPI server with Uvicorn...
python -m uvicorn app.main:app --reload

pause
