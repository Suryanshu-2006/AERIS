@echo off
title AERIS Ground Control Launcher
echo ======================================================================
echo   AERIS - Aerospace Engine Risk & Intelligence System
echo   DRDO SIH26054: AI-Enabled Real-Time Digital Twin System
echo ======================================================================
echo.

cd /d "%~dp0"

echo [*] Starting AERIS Backend Server on http://localhost:8000 ...
start "AERIS Backend Server (Port 8000)" cmd /k "cd /d "%~dp0" && python scripts/run_demo.py --server"

echo [*] Waiting 3 seconds for backend initialization ...
timeout /t 3 /nobreak >nul

echo [*] Starting AERIS Ground Control Frontend on http://localhost:5173 ...
start "AERIS Ground Control UI (Port 5173)" cmd /k "cd /d "%~dp0aerotwin\frontend" && npm run dev"

echo [*] Waiting 2 seconds for Vite dev server ...
timeout /t 2 /nobreak >nul

echo [*] Opening Ground Control Dashboard in default browser ...
start http://localhost:5173

echo.
echo ======================================================================
echo   [SUCCESS] AERIS System Launched Successfully!
echo.
echo   - Ground Control Station: http://localhost:5173
echo   - Backend REST API Docs:  http://localhost:8000/docs
echo   - Telemetry WebSocket:    ws://localhost:8000/ws/telemetry
echo.
echo   To stop the system, close the opened server terminal windows.
echo ======================================================================
echo.
pause
