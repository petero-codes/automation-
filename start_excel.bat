@echo off
setlocal EnableDelayedExpansion
title AI Autonomous Excel Financial Analyst Engine
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
echo        AI AUTONOMOUS EXCEL FINANCIAL ANALYST ENGINE (STANDALONE)
echo ===============================================================================
echo  [Process Cloak]  Enterprise Developer Services (Interactive Host)
echo  [Workload]       Microsoft Excel (Financial Modeling Workload)
echo  [Safety IRQ]     Move mouse (^>60px), click, Pause/F8/F9/F10, or double-tap ESC to yield
echo  [Auto-Resume]    2 minutes (120s) unbroken inactivity
echo ===============================================================================
echo.

cd /d "%PROJECT_ROOT%final_bot"
"%VENV_PY%" main.py --excel --now %*

echo.
echo Financial modeling session ended.
pause
