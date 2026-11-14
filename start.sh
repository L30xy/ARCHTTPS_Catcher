#!/usr/bin/env bash

# Ensure working directory is the script's directory
cd "$(dirname "$0")" || exit 1

# Read port from config.ini (default 27052)
PORT="27052"
if [ -f "config.ini" ]; then
    extracted_port=$(grep -i "^host" config.ini | awk -F':' '{print $2}' | tr -d ' \r\n')
    if [ -n "$extracted_port" ]; then
        PORT="$extracted_port"
    fi
fi

echo "===================================================="
echo "[1/4] Checking connected devices..."
if ! adb devices | awk 'NR>1 && $2=="device" {found=1} END {exit !found}'; then
    echo ""
    echo "[!] ERROR: No device found. Please connect your phone and enable USB Debugging."
    echo ""
    read -r -p "Press Enter to exit..."
    exit 1
fi

echo "[OK] Device connected."
echo ""

echo "[2/4] Cleaning up old run_ssl.py processes..."
pkill -f "run_ssl.py" >/dev/null 2>&1 || true

echo "[3/4] Rebuilding adb port forwarding (Port: $PORT)..."
adb forward --remove-all >/dev/null 2>&1
adb forward "tcp:$PORT" "tcp:$PORT" >/dev/null
echo "[OK] Port $PORT is ready."
echo ""

echo "[4/4] Starting Python Catcher..."
echo "----------------------------------------------------"
if command -v python3 >/dev/null 2>&1; then
    python3 run_ssl.py
else
    python run_ssl.py
fi

echo ""
echo "===================================================="
echo "[STOPPED] Script finished."
echo "===================================================="
read -r -p "Press Enter to exit..."