@echo off
title StreamVortex // Universal Stream Intelligence
cls
echo ========================================================
echo    StreamVortex - Universal Stream Intelligence Studio
echo ========================================================
echo.
echo Starting StreamVortex Control Center...
echo.
python -m ytdlp_smartstream.wizard
if %errorlevel% neq 0 (
    echo.
    echo [!] Running fallback Web Studio...
    python -m ytdlp_smartstream.cli --web
)
pause
