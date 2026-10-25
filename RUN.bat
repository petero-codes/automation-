@echo off
setlocal EnableDelayedExpansion
title Nextgen Autonomous Workforce Engine - VS Code and Excel

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
:: 3. CLEAN UP ANY OLD HANGING INSTANCES & STALE TEMP FILES
:: ----------------------------------------------------------------------
echo Cleaning up any old hanging instances and temporary files...
taskkill /F /IM python.exe /T >nul 2>&1
taskkill /F /IM excel.exe /T >nul 2>&1

:: Purge legacy shortcuts and artifacts if copied to an older machine
del /f /q "%USERPROFILE%\Desktop\*loggy*.lnk" >nul 2>&1
del /f /q "%USERPROFILE%\Desktop\*Loggy*.lnk" >nul 2>&1
del /f /q "%USERPROFILE%\Desktop\*nextgen*.lnk" >nul 2>&1
del /f /q "%USERPROFILE%\Desktop\*Nextgen*.lnk" >nul 2>&1
del /f /q "%USERPROFILE%\Desktop\~$*.xlsx" >nul 2>&1
del /f /q "%USERPROFILE%\Desktop\Workspaces\~$*.xlsx" >nul 2>&1
del /f /q "%USERPROFILE%\Desktop\Financial_Models\~$*.xlsx" >nul 2>&1
del /f /q "%PROJECT_ROOT%final_bot\startup_crash.log" >nul 2>&1
del /f /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\*loggy*.*" >nul 2>&1
del /f /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\*nextgen*.*" >nul 2>&1

echo ======================================================================
echo    NEXTGEN AUTONOMOUS WORKFORCE ENGINE - VS CODE AND EXCEL ONLY
echo ======================================================================
echo  * Dedicated Offline Productivity: Visual Studio Code and Microsoft Excel
echo  * Workday Lottery Pool: Software Engineering (VS Code) + Financial Analysis (Excel)
echo  * Instant Yield: Move mouse (^>60px), Click, or press [F8]/[F9]/[F10]/[PAUSE]
echo  * Resume: Press ENTER in console, [F8]/[F9]/[F10], or pause hands-off for 2 minutes
echo  * Terminate: Close console window (X) or Ctrl+C to terminate cleanly
echo ======================================================================
echo.

cd /d "%PROJECT_ROOT%final_bot"

if "%~1"=="" (
    echo [Nextgen Engine] Starting in immediate execution mode - Unified Workday: VS Code and Excel...
    "%VENV_PY%" "main.py" --workday --now
) else (
    "%VENV_PY%" "main.py" %*
)

echo.
echo Automation stopped. Press any key to exit.
pause
