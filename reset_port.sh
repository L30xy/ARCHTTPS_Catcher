#!/usr/bin/env bash

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
echo "[1/3] 正在检查 adb 设备连接状态..."
adb devices
echo ""

echo "[2/3] 正在清理旧的端口转发规则..."
adb forward --remove-all >/dev/null 2>&1
echo "清理完成。"
echo ""

echo "[3/3] 正在建立新的端口转发 (tcp:$PORT)..."
adb forward "tcp:$PORT" "tcp:$PORT" >/dev/null
echo ""

echo "----------------------------------------------------"
echo "当前生效的转发列表:"
adb forward --list
echo "----------------------------------------------------"
echo "[OK] 端口转发已重建完毕！(・ω・)"
echo "现在可以运行 ./start.sh 或 python3 run_ssl.py 开始抓包。"
echo "===================================================="
read -r -p "按回车键继续..."