@echo off
setlocal
title StreamVortex // Powered by yt-dlp
cd /d "%~dp0"

:: 1. Verify Python availability
where python >nul 2>&1
if %errorlevel% neq 0 (
    if exist "StreamVortex.exe" (
        echo [INFO] Python not detected, launching standalone StreamVortex.exe...
        start "" "StreamVortex.exe"
        exit /b 0
    )
    cls
    echo ========================================================================
    echo   [ERROR] Python is not installed or not found on PATH!
    echo ========================================================================
    echo.
    echo Please install Python 3.9+ from https://www.python.org/
    echo Make sure to check the box 'Add Python to PATH' during installation.
    echo.
    pause
    exit /b 1
)

:MENU
cls
echo ========================================================================
echo   StreamVortex v1.0.0 -- Universal Stream Studio (Powered by yt-dlp)
echo ========================================================================
echo   * Resilient Live and VOD Extractor Engine for yt-dlp
echo   * Universal HLS / DASH / M3U8 Stream Sniffer (Playwright CDP)
echo   * TikTok Live Watchdog, Lossless Recorder, and Native yt-dlp Plugin
echo ========================================================================
echo.
echo   [1] Launch Desktop GUI Studio (Recommended - Visual Window)
echo   [2] Launch Web Studio in Browser (http://127.0.0.1:8765)
echo   [3] Verify Global Environment (yt-dlp, FFmpeg, Playwright)
echo   [4] Launch Interactive Control Center (Terminal Wizard)
echo   [5] Run System Diagnostics (Doctor Health Check)
echo   [6] Build Standalone StreamVortex.exe
echo   [7] Open Downloads Folder
echo   [8] Exit
echo.
echo ========================================================================
set "CHOICE="
set /p CHOICE="  Select an option [1-8] (Default: 1): "

if "%CHOICE%"=="" set CHOICE=1
if "%CHOICE%"=="1" goto GUI
if "%CHOICE%"=="2" goto WEBUI
if "%CHOICE%"=="3" goto SETUP
if "%CHOICE%"=="4" goto WIZARD
if "%CHOICE%"=="5" goto DOCTOR
if "%CHOICE%"=="6" goto BUILD_EXE
if "%CHOICE%"=="7" goto OPEN_FOLDER
if "%CHOICE%"=="8" goto EXIT

echo.
echo [!] Invalid selection, please choose 1-8.
timeout /t 2 >nul
goto MENU

:GUI
cls
echo.
echo Launching StreamVortex Desktop Studio...
if exist "StreamVortex.exe" (
    start "" "StreamVortex.exe" --gui
) else (
    python -m ytdlp_smartstream.cli --gui
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
if exist "StreamVortex.exe" (
    "StreamVortex.exe" --web
) else (
    python -m ytdlp_smartstream.cli --web
)
pause
goto MENU

:SETUP
cls
echo.
echo [StreamVortex Setup] Verifying global binaries and system environment...
if exist "StreamVortex.exe" (
    "StreamVortex.exe" --setup
) else (
    python -m ytdlp_smartstream.cli --setup
)
echo.
pause
goto MENU

:WIZARD
cls
if exist "StreamVortex.exe" (
    "StreamVortex.exe" --wizard
) else (
    python -m ytdlp_smartstream.cli --wizard
)
pause
goto MENU

:DOCTOR
cls
if exist "StreamVortex.exe" (
    "StreamVortex.exe" --doctor
) else (
    python -m ytdlp_smartstream.cli --doctor
)
echo.
pause
goto MENU

:BUILD_EXE
cls
echo.
echo [Build] Compiling StreamVortex into a standalone executable (StreamVortex.exe)...
python build_exe.py
echo.
pause
goto MENU

:OPEN_FOLDER
cls
python -m ytdlp_smartstream.config
goto MENU

:EXIT
cls
echo Goodbye! Happy streaming.
timeout /t 1 >nul
exit /b 0
