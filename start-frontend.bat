@echo off
REM Windows batch script to start UC10 frontend React server

echo ========================================
echo UC10 Frontend - React Dev Server
echo ========================================
echo.

REM Change to frontend directory
cd /d "%~dp0frontend"

REM Install dependencies if needed
echo Installing Node.js dependencies...
call npm install

REM Start React dev server
echo.
echo Starting React dev server on http://localhost:5173
echo Press Ctrl+C to stop
echo.

call npm run dev

pause
