@echo off
title Zapway EV Newsroom Launcher
echo ===================================================
echo   LAUNCHING ZAPWAY EV NEWSROOM
echo ===================================================
echo.
cd /d "C:\Users\PIT\.gemini\antigravity\scratch\ZapwayNewsroom"

:: Start the Python backend in the background
echo 1. Starting Backend Server...
start "" cmd /k "python -m backend.main"

:: Wait for server to boot
timeout /t 3 /nobreak >nul

:: Open Zapway Newsroom UI in the default browser
echo 2. Opening Dashboard in Web Browser...
start http://localhost:8000/

echo.
echo ===================================================
echo   Zapway Newsroom is running!
echo   You can close this window.
echo ===================================================
exit
