@echo off
title Ceyel — Process Intelligence System
color 0A

echo.
echo  =========================================
echo    CEYEL - Process Intelligence System
echo  =========================================
echo.

:: Change to the directory where this bat file lives
cd /d "%~dp0"

:: ─── Step 1: Check Python ───────────────────────────────────────────────────
echo [1/4] Checking Python installation...
python --version >nul 2>&1
if errorlevel 1 (
    echo ERROR: Python is not installed or not in PATH.
    echo Please install Python 3.9+ from https://python.org
    pause
    exit /b 1
)
echo       OK - Python found.

:: ─── Step 2: Install dependencies ───────────────────────────────────────────
echo.
echo [2/4] Installing Python dependencies (this may take a minute)...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo ERROR: Failed to install dependencies.
    echo Please check your internet connection and try again.
    pause
    exit /b 1
)
echo       OK - Dependencies installed.

:: ─── Step 3: Pre-load sample data (if database is empty) ────────────────────
echo.
echo [3/4] Starting backend server...
echo       API will be available at http://localhost:8000
echo       Dashboard at            http://localhost:8000
echo       API Docs at             http://localhost:8000/docs
echo.

:: Start the FastAPI server in a new window so we can keep this window open
start "Ceyel Backend" cmd /k "cd /d %~dp0 && python -m uvicorn backend.main:app --host 0.0.0.0 --port 8000 --reload"

:: ─── Step 4: Wait and open browser ──────────────────────────────────────────
echo [4/4] Waiting for server to start...
timeout /t 4 /nobreak >nul

:: Open browser
start "" "http://localhost:8000"

echo.
echo  =========================================
echo    Ceyel is now running!
echo    Dashboard: http://localhost:8000
echo    API Docs:  http://localhost:8000/docs
echo  =========================================
echo.
echo  To load sample data, run:
echo    curl -X POST http://localhost:8000/api/events/bulk -H "Content-Type: application/json" -d @data/sample_events.json
echo.
echo  Press any key to exit this launcher (the server will keep running).
pause >nul
