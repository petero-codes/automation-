@echo off
setlocal EnableDelayedExpansion
title Loggy Bot - One-Click Installer

cd /d "%~dp0"
set "PROJECT_ROOT=%~dp0"

:: ----------------------------------------------------------------------
:: 1. CHECK ADMINISTRATOR PERMISSIONS & AUTO-ELEVATE
:: ----------------------------------------------------------------------
reg query "HKLM\SYSTEM\CurrentControlSet\Services\keyboard" >nul 2>&1
if %errorlevel% equ 0 goto AdminCheckPassed

net session >nul 2>&1
if %errorlevel% equ 0 goto AdminCheckPassed

echo ======================================================================
echo  ADMINISTRATOR PERMISSION REQUIRED
echo  Installing the Interception kernel filter driver requires admin rights.
echo  Requesting Administrator elevation...
echo ======================================================================
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process cmd -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
exit /b

:AdminCheckPassed

cls
echo ======================================================================
echo                    LOGGY BOT - ONE-CLICK INSTALLER
echo ======================================================================
echo  This automated installer will:
echo   [1] Purge obsolete files from previous or legacy systems
echo   [2] Detect or install Python 3.10+
echo   [3] Build an isolated virtual environment .venv
echo   [4] Install all required dependencies
echo   [5] Register the Interception kernel filter driver
echo ======================================================================
echo.

:: ----------------------------------------------------------------------
:: 2. PURGE OBSOLETE / LEGACY SYSTEM ARTIFACTS
:: ----------------------------------------------------------------------
echo Cleaning legacy system artifacts...
del /f /q "%USERPROFILE%\Desktop\*loggy*.lnk" >nul 2>&1
del /f /q "%USERPROFILE%\Desktop\*Loggy*.lnk" >nul 2>&1
del /f /q "%USERPROFILE%\Desktop\*nextgen*.lnk" >nul 2>&1
del /f /q "%USERPROFILE%\Desktop\*Nextgen*.lnk" >nul 2>&1
del /f /q "%PUBLIC%\Desktop\*loggy*.lnk" >nul 2>&1
del /f /q "%PUBLIC%\Desktop\*nextgen*.lnk" >nul 2>&1
del /f /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\*loggy*.*" >nul 2>&1
del /f /q "%APPDATA%\Microsoft\Windows\Start Menu\Programs\Startup\*nextgen*.*" >nul 2>&1
if exist "%PROJECT_ROOT%Nextgen_Workforce.exe" del /f /q "%PROJECT_ROOT%Nextgen_Workforce.exe" >nul 2>&1
if exist "%PROJECT_ROOT%..\Nextgen_Workforce.exe" del /f /q "%PROJECT_ROOT%..\Nextgen_Workforce.exe" >nul 2>&1
if exist "%PROJECT_ROOT%final_bot\idle_shorts.log" del /f /q "%PROJECT_ROOT%final_bot\idle_shorts.log" >nul 2>&1
if exist "%PROJECT_ROOT%final_bot\idle_firefox.log" del /f /q "%PROJECT_ROOT%final_bot\idle_firefox.log" >nul 2>&1
echo [✓] Legacy system files removed.
echo.

:: ----------------------------------------------------------------------
:: 3. DETECT OR AUTO-INSTALL PYTHON
:: ----------------------------------------------------------------------
echo [1/3] Checking Python installation...

set "PYTHON_EXE="

:: Search standard install folders (picks latest installed Python 3)
for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do if exist "%%D\python.exe" set "PYTHON_EXE=%%D\python.exe"
for /d %%D in ("C:\Program Files\Python3*") do if exist "%%D\python.exe" set "PYTHON_EXE=%%D\python.exe"
for /d %%D in ("C:\Python3*") do if exist "%%D\python.exe" set "PYTHON_EXE=%%D\python.exe"

if defined PYTHON_EXE goto PythonFound

:: Check PATH if not found in standard directories
for /f "delims=" %%I in ('where python.exe 2^>nul') do (
    set "PYTHON_EXE=%%I"
    goto PythonFound
)

for /f "delims=" %%I in ('where py.exe 2^>nul') do (
    set "PYTHON_EXE=%%I"
    goto PythonFound
)

:: Auto-install Python 3.11 if not found anywhere
echo.
echo Python was not detected on this computer.
echo Automatically downloading and installing Python 3.11...

where winget >nul 2>&1
if %errorlevel% equ 0 (
    echo Installing Python via Windows Package Manager winget...
    winget install --id Python.Python.3.11 --exact --source winget --silent --accept-package-agreements --accept-source-agreements
)

for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do if exist "%%D\python.exe" set "PYTHON_EXE=%%D\python.exe"
for /d %%D in ("C:\Program Files\Python3*") do if exist "%%D\python.exe" set "PYTHON_EXE=%%D\python.exe"

if defined PYTHON_EXE goto PythonFound

echo Downloading official Python installer...
powershell -NoProfile -ExecutionPolicy Bypass -Command "[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12; Invoke-WebRequest -Uri 'https://www.python.org/ftp/python/3.11.9/python-3.11.9-amd64.exe' -OutFile '$env:TEMP\python_setup.exe'"
echo Running silent Python setup...
"%TEMP%\python_setup.exe" /quiet InstallAllUsers=0 PrependPath=1 Include_test=0
del "%TEMP%\python_setup.exe" >nul 2>&1

for /d %%D in ("%LOCALAPPDATA%\Programs\Python\Python3*") do if exist "%%D\python.exe" set "PYTHON_EXE=%%D\python.exe"
for /d %%D in ("C:\Program Files\Python3*") do if exist "%%D\python.exe" set "PYTHON_EXE=%%D\python.exe"

if not defined PYTHON_EXE (
    echo [ERROR] Could not install Python automatically.
    echo Please install Python 3.10+ from https://www.python.org/downloads/ and rerun this installer.
    pause
    exit /b 1
)

:PythonFound
echo [✓] Using Python: "%PYTHON_EXE%"
echo.

:: ----------------------------------------------------------------------
:: 3. SETUP VIRTUAL ENVIRONMENT & INSTALL DEPENDENCIES
:: ----------------------------------------------------------------------
echo [2/3] Setting up virtual environment and dependencies...

set "VENV_DIR=%PROJECT_ROOT%.venv"
set "VENV_PY=%VENV_DIR%\Scripts\python.exe"
set "VENV_PIP=%VENV_DIR%\Scripts\pip.exe"

:: Validate existing venv (in case folder was copied from another machine)
if exist "%VENV_PY%" (
    "%VENV_PY%" -c "import sys" >nul 2>&1
    if !errorlevel! neq 0 (
        echo [!] Detected copied virtual environment from another machine. Rebuilding .venv...
        rmdir /s /q "%VENV_DIR%"
    )
)

if exist "%VENV_PY%" goto VenvReady
echo Creating virtual environment .venv...
"%PYTHON_EXE%" -m venv "%VENV_DIR%"
if %errorlevel% neq 0 (
    echo [ERROR] Failed to create virtual environment.
    pause
    exit /b 1
)

:VenvReady
echo Installing Python dependencies from requirements.txt...
"%VENV_PY%" -m pip install --quiet --upgrade pip
"%VENV_PIP%" install --quiet -r "%PROJECT_ROOT%requirements.txt"
if %errorlevel% neq 0 (
    echo Retrying dependencies installation with detailed output...
    "%VENV_PIP%" install -r "%PROJECT_ROOT%requirements.txt"
    if %errorlevel% neq 0 (
        echo [ERROR] Dependency installation failed.
        pause
        exit /b 1
    )
)

echo [✓] Python dependencies installed successfully.
echo.

:: ----------------------------------------------------------------------
:: 4. REGISTER INTERCEPTION KERNEL FILTER DRIVER
:: ----------------------------------------------------------------------
echo [3/3] Configuring Interception kernel filter driver...

set "INSTALLER_EXE="
if exist "%PROJECT_ROOT%Interception\install-interception.exe" (
    set "INSTALLER_EXE=%PROJECT_ROOT%Interception\install-interception.exe"
) else if exist "%PROJECT_ROOT%Interception\command line installer\install-interception.exe" (
    set "INSTALLER_EXE=%PROJECT_ROOT%Interception\command line installer\install-interception.exe"
)

if not defined INSTALLER_EXE (
    echo [ERROR] install-interception.exe was not found in Interception directory.
    pause
    exit /b 1
)

for %%I in ("%INSTALLER_EXE%") do set "INSTALLER_DIR=%%~dpI"

reg query "HKLM\SYSTEM\CurrentControlSet\Services\keyboard" >nul 2>&1
if %errorlevel% equ 0 (
    echo [✓] Interception filter driver is already registered with Windows.
    goto SetupFinished
)

echo Registering Interception filter driver with Windows...
cd /d "%INSTALLER_DIR%"
install-interception.exe /install
cd /d "%PROJECT_ROOT%"
echo [✓] Interception filter driver registered.

:SetupFinished
echo.

:: Clean up any legacy desktop shortcut if present
if exist "%USERPROFILE%\Desktop\Loggy Bot.lnk" del /f /q "%USERPROFILE%\Desktop\Loggy Bot.lnk" >nul 2>&1

:: ----------------------------------------------------------------------
:: 5. FINAL SUMMARY & ONE-TIME REBOOT PROMPT
:: ----------------------------------------------------------------------
echo ======================================================================
echo                     INSTALLATION SUCCESSFUL!
echo ======================================================================
echo  [✓] Python environment configured (.venv)
echo  [✓] All required packages installed
echo  [✓] Interception kernel driver registered
echo.
echo  CRITICAL: Windows requires a ONE-TIME COMPUTER RESTART for the
echo  hardware filter driver to bind to physical keyboard/mouse ports.
echo.
echo  After restarting, simply double-click RUN.bat whenever you want to use the bot.
echo ======================================================================
echo.

set "REBOOT_CHOICE=Y"
set /p "REBOOT_CHOICE=Would you like to restart your computer now? (Y/N) [Default: Y]: "
set "CLEAN_CHOICE=!REBOOT_CHOICE: =!"
if /i "!CLEAN_CHOICE!"=="N" (
    echo.
    echo Setup complete. Please restart your PC before running the bot.
    pause
    exit /b 0
)
if /i "!CLEAN_CHOICE!"=="NO" (
    echo.
    echo Setup complete. Please restart your PC before running the bot.
    pause
    exit /b 0
)

echo.
echo Restarting computer in 5 seconds...
shutdown /r /t 5 /c "Restarting to finalize Loggy Bot installation..."
exit /b 0
