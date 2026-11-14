#!/usr/bin/env bash

# Ensure working directory is the script's directory
cd "$(dirname "$0")" || exit 1

# Parse CLI flags (--skip-check or -s)
SKIP_ADB_CHECK=false
for arg in "$@"; do
    case "$arg" in
        --skip-check|-s)
            SKIP_ADB_CHECK=true
            ;;
    esac
done

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
HAS_ADB_DEVICE=false
if [ "$SKIP_ADB_CHECK" = true ]; then
    echo "[*] (--skip-check) Skipping ADB device check."
elif command -v adb >/dev/null 2>&1 && adb devices | awk 'NR>1 && $2=="device" {found=1} END {exit !found}'; then
    echo "[OK] Device connected."
    HAS_ADB_DEVICE=true
else
    echo ""
    echo "[!] WARNING: No ADB device detected (or ADB is unavailable)."
    read -r -p "Skip ADB check & port forwarding and continue anyway? (y/N): " skip_choice
    if [[ "${skip_choice,,}" == "y" ]]; then
        echo "[*] Skipping ADB device check..."
    else
        echo "[!] Aborted. Please connect your phone and enable USB Debugging."
        exit 1
    fi
fi
echo ""

echo "[2/4] Cleaning up old run_ssl.py processes..."
pkill -f "run_ssl.py" >/dev/null 2>&1 || true

echo "[3/4] Rebuilding adb port forwarding (Port: $PORT)..."
if [ "$HAS_ADB_DEVICE" = true ]; then
    adb forward --remove-all >/dev/null 2>&1
    adb forward "tcp:$PORT" "tcp:$PORT" >/dev/null
    echo "[OK] Port $PORT is ready."
else
    echo "[*] Skipped ADB port forwarding (assuming direct network host or external forwarding)."
fi
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