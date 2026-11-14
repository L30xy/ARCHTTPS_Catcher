@echo off
chcp 65001 >nul
title Config Editor / 配置修改工具
cd /d "%~dp0"

if not exist config.ini (
    (
        echo [frida]
        echo host = 127.0.0.1:27052
        echo gadget_name = Gadget
        echo.
        echo [output]
        echo output_dir = arc_logs
        echo language_file = zh-CN.json
        echo save_response_header = false
    ) > config.ini
)

:lang_select
cls
echo ====================================================
echo       Please select UI language / 请选择界面语言
echo ====================================================
echo  [1] 中文
echo  [2] English
echo ====================================================
set /p lang_choice="Choice / 输入(1 or 2): "

if "%lang_choice%"=="1" goto set_lang_zh
if "%lang_choice%"=="2" goto set_lang_en
goto lang_select

:set_lang_zh
set "msg_title=抓包配置修改工具"
set "msg_opt1=修改 Frida 端口/IP"
set "msg_opt2=修改 Gadget 进程名"
set "msg_opt3=修改 保存目录"
set "msg_opt4=修改 语言配置文件"
set "msg_opt5=切换 响应是否保留HTTP头"
set "msg_opt0=保存并退出"
set "msg_current=当前"
set "msg_prompt=请输入数字选择要修改的项: "
set "msg_enter_host=请输入新的 host (如 127.0.0.1:27052，直接回车保持不变): "
set "msg_enter_gadget=请输入新的 Gadget 名称 (直接回车保持不变): "
set "msg_enter_dir=请输入新的输出目录 (直接回车保持不变): "
set "msg_lang_hint=可选语言文件: zh-CN.json 或 en.json"
set "msg_enter_lang=请输入语言文件名 (直接回车保持不变): "
set "msg_saved=[OK] 配置已成功保存到 config.ini！"
set "msg_current_conf=当前配置内容如下："
goto load_config

:set_lang_en
set "msg_title=Capture Config Editor"
set "msg_opt1=Change Frida Port/IP"
set "msg_opt2=Change Gadget Name"
set "msg_opt3=Change Output Directory"
set "msg_opt4=Change Language Config File"
set "msg_opt5=Toggle Response HTTP Header"
set "msg_opt0=Save and Exit"
set "msg_current=Current"
set "msg_prompt=Enter number: "
set "msg_enter_host=Enter new host (e.g. 127.0.0.1:27052, press Enter to keep): "
set "msg_enter_gadget=Enter new Gadget name (press Enter to keep): "
set "msg_enter_dir=Enter new output directory (press Enter to keep): "
set "msg_lang_hint=Available: zh-CN.json or en.json"
set "msg_enter_lang=Enter language file name (press Enter to keep): "
set "msg_saved=[OK] Config successfully saved to config.ini!"
set "msg_current_conf=Current configuration:"
goto load_config

:load_config
set "cur_host=127.0.0.1:27052"
set "cur_gadget=Gadget"
set "cur_dir=arc_logs"
set "cur_lang=zh-CN.json"
set "cur_header=false"

for /f "tokens=1,* delims== " %%a in ('findstr /b /i "host" config.ini') do set "cur_host=%%b"
for /f "tokens=1,* delims== " %%a in ('findstr /b /i "gadget_name" config.ini') do set "cur_gadget=%%b"
for /f "tokens=1,* delims== " %%a in ('findstr /b /i "output_dir" config.ini') do set "cur_dir=%%b"
for /f "tokens=1,* delims== " %%a in ('findstr /b /i "language_file" config.ini') do set "cur_lang=%%b"
for /f "tokens=1,* delims== " %%a in ('findstr /b /i "save_response_header" config.ini') do set "cur_header=%%b"

for /f "tokens=* delims= " %%a in ("%cur_host%") do set "cur_host=%%a"
for /f "tokens=* delims= " %%a in ("%cur_gadget%") do set "cur_gadget=%%a"
for /f "tokens=* delims= " %%a in ("%cur_dir%") do set "cur_dir=%%a"
for /f "tokens=* delims= " %%a in ("%cur_lang%") do set "cur_lang=%%a"
for /f "tokens=* delims= " %%a in ("%cur_header%") do set "cur_header=%%a"

:menu
cls
echo ====================================================
echo                 %msg_title%
echo ====================================================
echo  [1] %msg_opt1% (%msg_current%: %cur_host%)
echo  [2] %msg_opt2% (%msg_current%: %cur_gadget%)
echo  [3] %msg_opt3% (%msg_current%: %cur_dir%)
echo  [4] %msg_opt4% (%msg_current%: %cur_lang%)
echo  [5] %msg_opt5% (%msg_current%: %cur_header%)
echo  [0] %msg_opt0%
echo ====================================================
set "choice="
set /p choice="%msg_prompt%"

if "%choice%"=="1" goto set_host
if "%choice%"=="2" goto set_gadget
if "%choice%"=="3" goto set_dir
if "%choice%"=="4" goto set_lang_file
if "%choice%"=="5" goto set_header
if "%choice%"=="0" goto save
goto menu

:set_host
echo.
set "input="
set /p input="%msg_enter_host%"
if not "%input%"=="" set "cur_host=%input%"
goto menu

:set_gadget
echo.
set "input="
set /p input="%msg_enter_gadget%"
if not "%input%"=="" set "cur_gadget=%input%"
goto menu

:set_dir
echo.
set "input="
set /p input="%msg_enter_dir%"
if not "%input%"=="" set "cur_dir=%input%"
goto menu

:set_lang_file
echo.
echo %msg_lang_hint%
set "input="
set /p input="%msg_enter_lang%"
if not "%input%"=="" set "cur_lang=%input%"
goto menu

:set_header
if /i "%cur_header%"=="true" (
    set "cur_header=false"
) else (
    set "cur_header=true"
)
goto menu

:save
(
    echo [frida]
    echo host = %cur_host%
    echo gadget_name = %cur_gadget%
    echo.
    echo [output]
    echo output_dir = %cur_dir%
    echo language_file = %cur_lang%
    echo save_response_header = %cur_header%
) > config.ini

echo.
echo %msg_saved%
echo.
echo %msg_current_conf%
echo ----------------------------------------------------
type config.ini
echo ----------------------------------------------------
echo.
pause