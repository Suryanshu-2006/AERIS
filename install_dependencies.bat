@echo off
title AERIS Dependency Installer
echo ======================================================================
echo   AERIS - Setup & Dependency Installer
echo   DRDO SIH26054: Aero Piston Engine Digital Twin System
echo ======================================================================
echo.

cd /d "%~dp0"

echo [1/2] Installing Backend Python Dependencies...
pip install -r aerotwin\backend\requirements.txt
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to install Python dependencies.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [2/2] Installing Frontend Node.js Dependencies...
cd aerotwin\frontend
call npm install
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Failed to install Node dependencies.
    pause
    exit /b %ERRORLEVEL%
)

cd /d "%~dp0"
echo.
echo ======================================================================
echo   [SUCCESS] All Backend and Frontend Dependencies Installed!
echo   You can now run start_aeris.bat to launch the application.
echo ======================================================================
pause
