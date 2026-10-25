@echo off
setlocal EnableDelayedExpansion
title AI Autonomous Workday Lottery Engine (Unified Starter)
cd /d "%~dp0"
set "PROJECT_ROOT=%~dp0"
set "VENV_DIR=%PROJECT_ROOT%.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"

if not exist "%VENV_PY%" (
    echo ===============================================================================
    echo  [!] First-time setup detected. Starting installer...
    echo ===============================================================================
    call "%PROJECT_ROOT%INSTALL.bat"
    exit /b
)

echo Cleaning up any old hanging instances...
taskkill /F /IM python.exe /T >nul 2>&1
taskkill /F /IM excel.exe /T >nul 2>&1

echo.
echo ===============================================================================
echo      AI AUTONOMOUS UNIFIED WORKDAY LOTTERY ENGINE (CODING & EXCEL)
echo ===============================================================================
echo  [Process Cloak]  Enterprise Developer Services (Interactive Host)
echo  [Workday Pool]   Software Engineering (VS Code) + Financial Modeling (Excel)
echo  [Task Lottery]   Stochastic lottery draw: completely unpredictable sequence
echo  [Safety IRQ]     Move mouse (^>60px), click, Pause/F8/F9/F10, or double-tap ESC to yield
echo  [Auto-Resume]    2 minutes (120s) unbroken inactivity
echo ===============================================================================
echo.

cd /d "%PROJECT_ROOT%final_bot"
"%VENV_PY%" main.py --workday --now %*

echo.
echo Workday session ended.
pause
