@echo off
REM Windows batch script to start UC10 backend FastAPI server

echo ========================================
echo UC10 Backend - FastAPI Server
echo ========================================
echo.

REM Change to backend directory
cd /d "%~dp0backend"

REM Install dependencies if needed
echo Installing Python dependencies...
pip install -r requirements.txt

REM Start FastAPI server
echo.
echo Starting FastAPI server on http://localhost:8000
echo Press Ctrl+C to stop
echo.

py -m uvicorn main:app --host 0.0.0.0 --port 8000 --reload

pause
