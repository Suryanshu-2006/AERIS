@echo off
title AERIS 17-Step Flight Storyline Demo
echo ======================================================================
echo   AERIS - 17-Step Flight Storyline Demo (DRDO SIH26054)
echo ======================================================================
echo.

cd /d "%~dp0"
python scripts/run_demo.py --cli

echo.
echo ======================================================================
echo   Demo run finished. Press any key to exit this window.
echo ======================================================================
pause >nul
