@echo off
setlocal
title Interception Driver Uninstaller
cd /d "%~dp0"
set "PROJECT_ROOT=%~dp0"

:: ----------------------------------------------------------------------
:: 1. CHECK ADMINISTRATOR PERMISSIONS & AUTO-ELEVATE
:: ----------------------------------------------------------------------
net session >nul 2>&1
if %errorlevel% neq 0 (
    echo Requesting Administrator privileges to uninstall driver...
    powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process cmd -ArgumentList '/c \"\"%~f0\"\"' -Verb RunAs"
    exit /b
)

:: ----------------------------------------------------------------------
:: 2. LOCATE INSTALLER EXECUTABLE
:: ----------------------------------------------------------------------
set "INSTALLER_EXE="
if exist "%PROJECT_ROOT%Interception\install-interception.exe" (
    set "INSTALLER_EXE=%PROJECT_ROOT%Interception\install-interception.exe"
) else if exist "%PROJECT_ROOT%Interception\command line installer\install-interception.exe" (
    set "INSTALLER_EXE=%PROJECT_ROOT%Interception\command line installer\install-interception.exe"
)

if not defined INSTALLER_EXE (
    echo [ERROR] Could not find install-interception.exe
    pause
    exit /b 1
)

for %%I in ("%INSTALLER_EXE%") do set "INSTALLER_DIR=%%~dpI"
cd /d "%INSTALLER_DIR%"

echo ======================================================================
echo  Uninstalling Interception Kernel Filter Driver...
echo ======================================================================
echo.

install-interception.exe /uninstall

echo.
echo ======================================================================
echo  Driver uninstalled successfully!
echo  Please restart your computer to finalize removal of the filter driver.
echo ======================================================================
echo.
pause
