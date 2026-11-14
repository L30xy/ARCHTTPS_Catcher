#!/usr/bin/env bash

cd "$(dirname "$0")" || exit 1

if [ ! -f "config.ini" ]; then
    cat << 'EOF' > config.ini
[frida]
host = 127.0.0.1:27052
gadget_name = Gadget

[output]
output_dir = arc_logs
language_file = zh-CN.json
save_response_header = false
EOF
fi

# Select UI Language
while true; do
    clear
    echo "===================================================="
    echo "      Please select UI language / 请选择界面语言"
    echo "===================================================="
    echo " [1] 中文"
    echo " [2] English"
    echo "===================================================="
    read -r -p "Choice / 输入(1 or 2): " lang_choice
    if [ "$lang_choice" = "1" ]; then
        msg_title="抓包配置修改工具"
        msg_opt1="修改 Frida 端口/IP"
        msg_opt2="修改 Gadget 进程名"
        msg_opt3="修改 保存目录"
        msg_opt4="修改 语言配置文件"
        msg_opt5="切换 响应是否保留HTTP头"
        msg_opt0="保存并退出"
        msg_current="当前"
        msg_prompt="请输入数字选择要修改的项: "
        msg_enter_host="请输入新的 host (如 127.0.0.1:27052，直接回车保持不变): "
        msg_enter_gadget="请输入新的 Gadget 名称 (直接回车保持不变): "
        msg_enter_dir="请输入新的输出目录 (直接回车保持不变): "
        msg_lang_hint="可选语言文件: zh-CN.json 或 en.json"
        msg_enter_lang="请输入语言文件名 (直接回车保持不变): "
        msg_saved="[OK] 配置已成功保存到 config.ini！"
        msg_current_conf="当前配置内容如下："
        break
    elif [ "$lang_choice" = "2" ]; then
        msg_title="Capture Config Editor"
        msg_opt1="Change Frida Port/IP"
        msg_opt2="Change Gadget Name"
        msg_opt3="Change Output Directory"
        msg_opt4="Change Language Config File"
        msg_opt5="Toggle Response HTTP Header"
        msg_opt0="Save and Exit"
        msg_current="Current"
        msg_prompt="Enter number: "
        msg_enter_host="Enter new host (e.g. 127.0.0.1:27052, press Enter to keep): "
        msg_enter_gadget="Enter new Gadget name (press Enter to keep): "
        msg_enter_dir="Enter new output directory (press Enter to keep): "
        msg_lang_hint="Available: zh-CN.json or en.json"
        msg_enter_lang="Enter language file name (press Enter to keep): "
        msg_saved="[OK] Config successfully saved to config.ini!"
        msg_current_conf="Current configuration:"
        break
    fi
done

# Helper to read ini values
get_ini_val() {
    local key="$1"
    local default_val="$2"
    local val
    val=$(grep -i "^[[:space:]]*${key}[[:space:]]*=" config.ini | head -n 1 | cut -d'=' -f2- | sed 's/^[[:space:]]*//;s/[[:space:]\r]*$//')
    if [ -n "$val" ]; then
        echo "$val"
    else
        echo "$default_val"
    fi
}

cur_host=$(get_ini_val "host" "127.0.0.1:27052")
cur_gadget=$(get_ini_val "gadget_name" "Gadget")
cur_dir=$(get_ini_val "output_dir" "arc_logs")
cur_lang=$(get_ini_val "language_file" "zh-CN.json")
cur_header=$(get_ini_val "save_response_header" "false")

# Main Menu Loop
while true; do
    clear
    echo "===================================================="
    echo "                $msg_title"
    echo "===================================================="
    echo " [1] $msg_opt1 ($msg_current: $cur_host)"
    echo " [2] $msg_opt2 ($msg_current: $cur_gadget)"
    echo " [3] $msg_opt3 ($msg_current: $cur_dir)"
    echo " [4] $msg_opt4 ($msg_current: $cur_lang)"
    echo " [5] $msg_opt5 ($msg_current: $cur_header)"
    echo " [0] $msg_opt0"
    echo "===================================================="
    read -r -p "$msg_prompt" choice

    case "$choice" in
        1)
            echo ""
            read -r -p "$msg_enter_host" input
            [ -n "$input" ] && cur_host="$input"
            ;;
        2)
            echo ""
            read -r -p "$msg_enter_gadget" input
            [ -n "$input" ] && cur_gadget="$input"
            ;;
        3)
            echo ""
            read -r -p "$msg_enter_dir" input
            [ -n "$input" ] && cur_dir="$input"
            ;;
        4)
            echo ""
            echo "$msg_lang_hint"
            read -r -p "$msg_enter_lang" input
            [ -n "$input" ] && cur_lang="$input"
            ;;
        5)
            if [[ "${cur_header,,}" == "true" ]]; then
                cur_header="false"
            else
                cur_header="true"
            fi
            ;;
        0)
            cat << EOF > config.ini
[frida]
host = $cur_host
gadget_name = $cur_gadget

[output]
output_dir = $cur_dir
language_file = $cur_lang
save_response_header = $cur_header
EOF
            echo ""
            echo "$msg_saved"
            echo ""
            echo "$msg_current_conf"
            echo "----------------------------------------------------"
            cat config.ini
            echo "----------------------------------------------------"
            echo ""
            read -r -p "Press Enter to exit..."
            break
            ;;
    esac
done