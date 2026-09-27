@echo off
title AERIS Automated Engineering Validation Suite
echo ======================================================================
echo   AERIS - Automated Engineering Validation & Verification Suite
echo   DRDO SIH26054: Aero Piston Engine Digital Twin
echo ======================================================================
echo.

cd /d "%~dp0"
python scripts/run_validation.py

echo.
echo ======================================================================
echo   Validation suite finished. Press any key to exit this window.
echo ======================================================================
pause >nul
