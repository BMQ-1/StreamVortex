@echo off
setlocal enabledelayedexpansion
title StreamVortex // Universal Stream Intelligence Studio (Powered by yt-dlp)
cd /d "%~dp0"

:: Set console encoding to UTF-8
chcp 65001 >nul 2>&1

:: Verify Python is installed and accessible
where python >nul 2>&1
if %errorlevel% neq 0 (
    cls
    echo ========================================================================
    echo   [ERROR] Python was not found in your system PATH!
    echo ========================================================================
    echo.
    echo Please install Python 3.9 or higher from:
    echo   https://www.python.org/
    echo.
    echo IMPORTANT: Make sure to check the box "Add Python to PATH" during installation.
    echo.
    pause
    exit /b 1
)

:MENU
cls
echo ========================================================================
echo   StreamVortex v1.0.0 -- Stream Intelligence Studio (Powered by yt-dlp)
echo ========================================================================
echo   * Resilient Live ^& VOD Extractor Engine for yt-dlp
echo   * Universal HLS / DASH / M3U8 Stream Sniffer (Playwright CDP)
echo   * TikTok Live Watchdog, Recorder, and Native yt-dlp Plugin
echo ========================================================================
echo.
echo   [1] ⚡ Launch Control Center (Interactive Terminal Wizard)
echo   [2] 🌐 Launch Web Studio (Browser GUI with Video Player)
echo   [3] 🩺 Run System Diagnostics ^& yt-dlp Health Check
echo   [4] 🔌 Install / Update Native yt-dlp Plugin
echo   [5] 📁 Open Downloads Folder
echo   [6] 🚪 Exit
echo.
echo ========================================================================
set "CHOICE="
set /p CHOICE="  Select an option [1-6] (Default: 1): "

if "%CHOICE%"=="" set CHOICE=1
if "%CHOICE%"=="1" goto WIZARD
if "%CHOICE%"=="2" goto WEBUI
if "%CHOICE%"=="3" goto DOCTOR
if "%CHOICE%"=="4" goto PLUGIN
if "%CHOICE%"=="5" goto OPEN_FOLDER
if "%CHOICE%"=="6" goto EXIT

echo.
echo [!] Invalid selection, please choose 1-6.
timeout /t 2 >nul
goto MENU

:WIZARD
cls
python -m ytdlp_smartstream.cli --wizard
if %errorlevel% neq 0 (
    echo.
    echo [!] Interactive wizard closed or encountered an issue.
    pause
)
goto MENU

:WEBUI
cls
echo.
echo ========================================================================
echo   Starting StreamVortex Web Studio at http://127.0.0.1:8765 ...
echo   (Press Ctrl+C to stop the Web Studio server)
echo ========================================================================
echo.
python -m ytdlp_smartstream.cli --web
pause
goto MENU

:DOCTOR
cls
python -m ytdlp_smartstream.cli --doctor
echo.
pause
goto MENU

:PLUGIN
cls
echo.
echo Linking StreamVortex extractors into yt-dlp native plugins directory...
python install_plugin.py
echo.
pause
goto MENU

:OPEN_FOLDER
cls
python -c "from ytdlp_smartstream.config import get_download_dir; import os, sys; os.startfile(str(get_download_dir())) if sys.platform=='win32' else None"
goto MENU

:EXIT
cls
echo Goodbye! Happy streaming.
timeout /t 1 >nul
exit /b 0
