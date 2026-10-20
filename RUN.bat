@echo off
setlocal EnableDelayedExpansion
title Loggy Bot

cd /d "%~dp0"
set "PROJECT_ROOT=%~dp0"

:: ----------------------------------------------------------------------
:: 1. CHECK VIRTUAL ENVIRONMENT & VALIDATE PORTABILITY
:: ----------------------------------------------------------------------
set "VENV_DIR=%PROJECT_ROOT%.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"

if not exist "%VENV_PY%" (
    echo ======================================================================
    echo  [!] First-time setup detected. Starting installer...
    echo ======================================================================
    call "%PROJECT_ROOT%INSTALL.bat"
    exit /b
)

:: Test if virtual environment works on this machine (in case folder was copied)
"%VENV_PY%" -c "import sys" >nul 2>&1
if %errorlevel% neq 0 (
    echo ======================================================================
    echo  [!] Detected copied virtual environment from another computer.
    echo  Starting installer to rebuild .venv for this machine...
    echo ======================================================================
    call "%PROJECT_ROOT%INSTALL.bat"
    exit /b
)

:: ----------------------------------------------------------------------
:: 2. VERIFY DRIVER IS ACTIVE IN KERNEL MEMORY
:: ----------------------------------------------------------------------
"%VENV_PY%" -c "import interception; ctx = interception.requires_driver.__globals__['_g_context']; exit(0 if ctx.valid else 1)" >nul 2>&1
if %errorlevel% neq 0 (
    echo ======================================================================
    echo                     RESTART REQUIRED
    echo ======================================================================
    echo  The Interception driver is registered, but Windows has not been
    echo  restarted yet. The hardware driver only activates upon a reboot.
    echo ======================================================================
    echo.
    set "REBOOT_CHOICE=Y"
    set /p REBOOT_CHOICE="Would you like to restart your computer now? (Y/N) [Default: Y]: "
    if /i "!REBOOT_CHOICE!"=="N" (
        echo.
        echo Please restart your PC before running the bot.
        pause
        exit /b 0
    )
    if /i "!REBOOT_CHOICE!"=="NO" (
        echo.
        echo Please restart your PC before running the bot.
        pause
        exit /b 0
    )
    shutdown /r /t 5 /c "Restarting to activate Interception driver..."
    exit /b 0
)

:: ----------------------------------------------------------------------
:: 3. LAUNCH LOGGY BOT
:: ----------------------------------------------------------------------
echo ======================================================================
echo                  LOGGY AUTOMATION BOT IS RUNNING
echo ======================================================================
echo  * The bot will monitor for idle and start tasks automatically.
echo  * Move your mouse or double-tap ESC anytime to take back control.
echo  * Keep this window open or minimized while the bot runs.
echo ======================================================================
echo.

cd /d "%PROJECT_ROOT%final_bot"

set "TARGET_SCRIPT=main_shorts.py"
if /i "%~1"=="firefox" set "TARGET_SCRIPT=main_firefox.py"
if /i "%~1"=="chrome"  set "TARGET_SCRIPT=main_chrome.py"
if /i "%~1"=="edge"    set "TARGET_SCRIPT=main_edge.py"

"%VENV_PY%" "%TARGET_SCRIPT%"

echo.
echo Automation stopped. Press any key to exit.
pause
