@echo off
cd /d "%~dp0"

set "PORT=27052"
if exist config.ini (
    for /f "tokens=2 delims=:" %%a in ('findstr /b /i "host" config.ini') do (
        set "PORT=%%a"
    )
)
for /f "tokens=* delims= " %%a in ("%PORT%") do set "PORT=%%a"

title Reset ADB Port Forwarding (%PORT%)

echo ====================================================
echo [1/3] Checking connected ADB devices...
adb devices
echo.

echo [2/3] Removing old port forwarding rules...
adb forward --remove-all >nul 2>&1
echo Done.
echo.

echo [3/3] Forwarding tcp:%PORT% to tcp:%PORT%...
adb forward tcp:%PORT% tcp:%PORT% >nul
echo.

echo ----------------------------------------------------
echo Active forwarding rules:
adb forward --list
echo ----------------------------------------------------
echo [OK] Port forwarding rebuilt successfully!
echo You can now run start.bat or python run_ssl.py.
echo ====================================================
pause