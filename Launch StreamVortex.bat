@echo off
setlocal EnableExtensions EnableDelayedExpansion
title StreamVortex // Powered by yt-dlp
chcp 65001 >nul 2>&1

:: Set working directory to the script's own folder
cd /d "%~dp0"

:: ============================================================================
:: 1. Intelligent Python & Standalone Executable Discovery
:: ============================================================================
set "PYTHON_EXE="
set "CLI_CMD="

:: Test if system 'python' command is functional (and filter out broken WindowsApps shims)
for /f "delims=" %%I in ('where python 2^>nul') do (
    if "!PYTHON_EXE!"=="" (
        set "CAND_PY=%%I"
        echo !CAND_PY! | findstr /i "WindowsApps" >nul 2>&1
        if !errorlevel! neq 0 (
            "!CAND_PY!" -c "import sys; sys.exit(0)" >nul 2>&1
            if !errorlevel! equ 0 (
                set "PYTHON_EXE=!CAND_PY!"
            )
        )
    )
)

:: Test Python launcher 'py -3' if python command was not resolved
if "!PYTHON_EXE!"=="" (
    py -3 -c "import sys; sys.exit(0)" >nul 2>&1
    if !errorlevel! equ 0 (
        set "PYTHON_EXE=py -3"
    )
)

:: Search standard Windows installation directories
if "!PYTHON_EXE!"=="" (
    for %%P in (
        "%LOCALAPPDATA%\Programs\Python\Python313\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python312\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python311\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python310\python.exe"
        "%LOCALAPPDATA%\Programs\Python\Python39\python.exe"
        "C:\Python313\python.exe"
        "C:\Python312\python.exe"
        "C:\Python311\python.exe"
        "C:\Python310\python.exe"
        "C:\Program Files\Python313\python.exe"
        "C:\Program Files\Python312\python.exe"
        "C:\Program Files\Python311\python.exe"
        "C:\Program Files\Python310\python.exe"
    ) do (
        if "!PYTHON_EXE!"=="" (
            if exist %%P (
                %%P -c "import sys; sys.exit(0)" >nul 2>&1
                if !errorlevel! equ 0 set "PYTHON_EXE=%%~P"
            )
        )
    )
)

:: Configure execution command
if not "!PYTHON_EXE!"=="" (
    set "CLI_CMD="!PYTHON_EXE!" -m ytdlp_smartstream.cli"
) else if exist "StreamVortex.exe" (
    set "CLI_CMD=".\StreamVortex.exe""
)

:: If neither Python nor StreamVortex.exe is present, offer 1-click Python setup
if "!CLI_CMD!"=="" (
    cls
    echo ========================================================================
    echo   StreamVortex - First Time Setup Required
    echo ========================================================================
    echo.
    echo   Neither Python 3.9+ nor StreamVortex.exe was detected on this PC.
    echo.
    set "INSTALL_PY=Y"
    set /p INSTALL_PY="  Auto-download and configure official Python 3.11 now? (Y/N) [Y]: "
    if not defined INSTALL_PY set "INSTALL_PY=Y"
    if /i not "!INSTALL_PY!"=="Y" goto NO_INSTALL

    echo.
    echo   [1/2] Downloading official Python 3.11 Windows 64-bit installer...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile '%TEMP%\python_installer.exe'"
    echo   [2/2] Installing Python with PATH registration...
    "%TEMP%\python_installer.exe" /passive InstallAllUsers=0 Include_launcher=1 PrependPath=1 Include_pip=1
    echo.
    echo   [+] Python installed! Please restart this launcher.
    pause
    exit /b 0

    :NO_INSTALL
    echo.
    echo Please install Python 3.9+ from https://www.python.org/
    echo Be sure to check 'Add Python to PATH' during installation.
    echo.
    pause
    exit /b 1
)

:: ============================================================================
:: 2. Launch Interactive CLI or Forward Drag-and-Drop / Arguments
:: ============================================================================
if not "%~1"=="" (
    set "ARG1=%~1"

    :: Case A: CLI Option Flag passed (e.g. --gui, --web, --doctor)
    if "!ARG1:~0,1!"=="-" (
        !CLI_CMD! %*
        goto FINISH
    )

    :: Case B: URL passed directly (http://, https://, or smart:)
    if /i "!ARG1:~0,4!"=="http" (
        !CLI_CMD! "%~1"
        goto FINISH
    )
    if /i "!ARG1:~0,6!"=="smart:" (
        !CLI_CMD! "%~1"
        goto FINISH
    )

    :: Case C: File or Folder Dragged and Dropped for Container Repair
    !CLI_CMD! --fix "%~1"
    goto FINISH
)

:: Direct double-click without arguments:
:: Immediately launch the exact same interactive CLI with up and down arrow keys used by the exe!
!CLI_CMD!

:FINISH
if %errorlevel% neq 0 (
    echo.
    pause
)
exit /b %errorlevel%
