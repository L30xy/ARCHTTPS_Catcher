@echo off
chcp 65001 >nul
title Frida SSL Catcher
cd /d "%~dp0"

rem Read port from config.ini (default 27052)
set "PORT=27052"
if exist config.ini (
    for /f "tokens=2 delims=:" %%a in ('findstr /b /i "host" config.ini') do (
        set "PORT=%%a"
    )
)
for /f "tokens=* delims= " %%a in ("%PORT%") do set "PORT=%%a"

echo ====================================================
echo [1/4] Checking connected devices...
for /f "tokens=2" %%i in ('adb devices') do (
    if "%%i"=="device" goto device_found
)
echo.
echo [!] ERROR: No device found. Please connect your phone and enable USB Debugging.
echo.
pause
exit /b

:device_found
echo [OK] Device connected.
echo.

echo [2/4] Cleaning up old run_ssl.py processes...
wmic process where "name='python.exe' and commandline like '%%run_ssl.py%%'" call terminate >nul 2>&1

echo [3/4] Rebuilding adb port forwarding (Port: %PORT%)...
adb forward --remove-all >nul 2>&1
adb forward tcp:%PORT% tcp:%PORT% >nul
echo [OK] Port %PORT% is ready.
echo.

echo [4/4] Starting Python Catcher...
echo ----------------------------------------------------
python run_ssl.py

echo.
echo ====================================================
echo [STOPPED] Script finished.
echo ====================================================
pause