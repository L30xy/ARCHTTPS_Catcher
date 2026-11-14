import os
import sys
import glob
import json
import re
import time
import configparser


def clear_screen():
    os.system('cls' if os.name == 'nt' else 'clear')


def get_configured_log_dir():
    """从 config.ini 动态读取日志目录，若无则回退至 arc_logs"""
    base_dir = os.path.dirname(os.path.abspath(__file__))
    ini_path = os.path.join(base_dir, 'config.ini')
    log_dir_name = 'arc_logs'

    if os.path.exists(ini_path):
        try:
            config = configparser.ConfigParser()
            config.read(ini_path, encoding='utf-8')
            log_dir_name = config.get('output', 'output_dir', fallback='arc_logs').strip()
        except Exception:
            pass

    return os.path.abspath(os.path.join(base_dir, log_dir_name))


def strip_http_header_and_chunks(text):
    """剥离 HTTP 头部与可能残留的 Chunked 十六进制分块长度标记"""
    text = text.replace("\r\n", "\n")

    # 若以 HTTP/ 开头或前几行包含标准 HTTP Header，直接定位空行切出 Body
    first_line = text.split("\n", 1)[0]
    if first_line.startswith(("HTTP/", "GET ", "POST ", "PUT ", "DELETE ")):
        sep_idx = text.find("\n\n")
        if sep_idx != -1:
            text = text[sep_idx + 2:]

    # 尝试直接解析；若因夹杂 chunked 长度行失败，则在后续提供清洗版本
    cleaned_chunk = re.sub(r'(?m)^[0-9a-fA-F]{1,8}\n', '', text)
    cleaned_chunk = re.sub(r'(?m)^0\n*$', '', cleaned_chunk).strip()
    return text.strip(), cleaned_chunk


def extract_json_from_text(text):
    """从文本中提取最完整的合法 JSON 对象或数组"""
    decoder = json.JSONDecoder()
    valid_jsons = []
    length = len(text)
    idx = 0

    while idx < length:
        # 同时支持查找对象 '{' 与数组 '['
        next_obj = text.find('{', idx)
        next_arr = text.find('[', idx)

        candidates = [pos for pos in (next_obj, next_arr) if pos != -1]
        if not candidates:
            break

        idx = min(candidates)
        try:
            data, offset = decoder.raw_decode(text[idx:])
            # 过滤非容器类型及残留的极小假数据
            if isinstance(data, (dict, list)):
                if isinstance(data, dict) and ("cf-nel" in data or "report_to" in data):
                    idx += offset
                    continue
                valid_jsons.append(data)
            idx += offset
        except json.JSONDecodeError:
            idx += 1

    if not valid_jsons:
        return None

    # 若存在多个 JSON 块，返回序列化后体积最大的一个（即核心业务负载）
    return max(valid_jsons, key=lambda x: len(json.dumps(x, ensure_ascii=False)))


def extract_and_format(filepath, delete_source_txt=False):
    """核心处理逻辑：提取 JSON 并格式化保存"""
    try:
        with open(filepath, "r", encoding="utf-8-sig", errors="replace") as f:
            content = f.read().strip()

        if not content:
            return False

        is_json_ext = filepath.lower().endswith('.json')
        json_data = None

        if is_json_ext:
            try:
                json_data = json.loads(content)
            except json.JSONDecodeError:
                print(f"[-] 跳过损坏的 JSON 文件: {os.path.basename(filepath)}")
                return False
        else:
            # 1. 先剥离 HTTP 头并尝试提取
            raw_body, chunk_cleaned_body = strip_http_header_and_chunks(content)
            json_data = extract_json_from_text(raw_body)

            # 2. 若因残留 Chunked 分块标记导致失败，使用清洗后的文本重试
            if json_data is None and chunk_cleaned_body != raw_body:
                json_data = extract_json_from_text(chunk_cleaned_body)

            if json_data is None:
                print(f"[-] 跳过 (无 JSON 负载): {os.path.basename(filepath)}")
                return False

        formatted_json = json.dumps(json_data, indent=4, ensure_ascii=False)
        base_name = os.path.splitext(filepath)[0]
        json_filepath = base_name + ".json"

        # 如果目标 JSON 文件内容已经完全一致，跳过写入以节省磁盘 I/O
        if os.path.exists(json_filepath):
            try:
                with open(json_filepath, "r", encoding="utf-8") as f_exist:
                    if f_exist.read() == formatted_json:
                        print(f"[=] 已是最新格式，跳过: {os.path.basename(json_filepath)}")
                        return True
            except Exception:
                pass

        with open(json_filepath, "w", encoding="utf-8") as f_out:
            f_out.write(formatted_json)

        if not is_json_ext and delete_source_txt and os.path.exists(json_filepath):
            try:
                os.remove(filepath)
            except OSError:
                pass

        print(f"[+] 格式化成功: {os.path.basename(json_filepath)}")
        return True

    except Exception as e:
        print(f"[-] 处理异常 {os.path.basename(filepath)}: {e}")
        return False


def collect_target_files(target_dir, include_subdir, only_response_dir=False):
    """收集待处理的目标文件，自动排除项目自身的配置目录并去重"""
    script_dir = os.path.dirname(os.path.abspath(__file__))
    exclude_dirs = {
        os.path.abspath(os.path.join(script_dir, "language")),
        os.path.abspath(os.path.join(script_dir, ".git")),
        os.path.abspath(os.path.join(script_dir, "__pycache__")),
        os.path.abspath(os.path.join(script_dir, "venv")),
    }

    if only_response_dir:
        pattern = os.path.join(target_dir, "**", "*_response", "*.*")
        raw_files = glob.glob(pattern, recursive=True)
    elif include_subdir:
        pattern = os.path.join(target_dir, "**", "*.*")
        raw_files = glob.glob(pattern, recursive=True)
    else:
        pattern = os.path.join(target_dir, "*.*")
        raw_files = glob.glob(pattern)

    # 过滤后缀与排除目录
    filtered = []
    txt_basenames = set()

    for f in raw_files:
        abs_f = os.path.abspath(f)
        if any(abs_f.startswith(ex_dir + os.sep) for ex_dir in exclude_dirs):
            continue
        lower_f = abs_f.lower()
        if lower_f.endswith('.txt'):
            txt_basenames.add(os.path.splitext(abs_f)[0])
            filtered.append(abs_f)
        elif lower_f.endswith('.json'):
            filtered.append(abs_f)

    # 去重：如果同一个目录下既有 xxx.txt 又有 xxx.json，只处理 xxx.txt 避免重复操作两次
    final_targets = []
    for f in filtered:
        if f.lower().endswith('.json') and os.path.splitext(f)[0] in txt_basenames:
            continue
        final_targets.append(f)

    return final_targets


def format_single_file():
    """处理单个文件"""
    file_path = input("\n请输入文件的绝对路径 (或直接把文件拖拽到此处): ").strip()
    file_path = file_path.strip('"').strip("'")

    if not os.path.isfile(file_path):
        print(f"\n[!] 错误: 找不到文件 -> {file_path}")
        return

    extract_and_format(file_path)


def process_directory(target_dir, include_subdir, only_response_dir=False):
    """批量处理指定目录"""
    if not os.path.exists(target_dir):
        print(f"\n[!] 错误: 目录不存在 -> {target_dir}")
        return

    print(f"\n[*] 正在扫描目录: {target_dir}")
    targets = collect_target_files(target_dir, include_subdir, only_response_dir)

    if not targets:
        print("[-] 没有找到待处理的 .txt 或 .json 文件。")
        return

    has_txt = any(f.lower().endswith('.txt') for f in targets)
    delete_txt = False
    if has_txt:
        del_choice = input(f"[*] 共找到 {len(targets)} 个目标文件。转换成功后是否删除原 .txt 文件? (y/n, 默认 n): ").strip().lower()
        delete_txt = (del_choice == 'y')
    else:
        print(f"[*] 共找到 {len(targets)} 个目标文件，开始处理...\n")

    start_time = time.time()
    count = 0
    for filepath in targets:
        if extract_and_format(filepath, delete_source_txt=delete_txt):
            count += 1

    elapsed = time.time() - start_time
    print(f"\n[*] 处理完成！成功格式化 {count}/{len(targets)} 个文件 (耗时 {elapsed:.2f} 秒)。")


def main():
    # 支持直接将文件或文件夹拖拽到脚本图标上运行 (CLI 参数支持)
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            path = os.path.abspath(arg.strip('"').strip("'"))
            if os.path.isfile(path):
                extract_and_format(path)
            elif os.path.isdir(path):
                process_directory(path, include_subdir=True)
        input("\n按回车键退出...")
        return

    while True:
        clear_screen()
        log_dir = get_configured_log_dir()
        log_dir_name = os.path.basename(log_dir)

        print("====================================================")
        print("                JSON 提取与格式化工具")
        print("====================================================")
        print(" [1] 格式化 单个文件")
        print(" [2] 格式化 本目录 下所有 txt / json")
        print(" [3] 格式化 指定目录 下所有 txt / json")
        print(f" [4] 批量格式化抓包记录 ({log_dir_name}/*_response)")
        print(" [0] 退出")
        print("====================================================")

        choice = input("请输入数字选择操作: ").strip()

        if choice == "1":
            format_single_file()
            input("\n按回车键返回主菜单...")

        elif choice == "2":
            subdir_choice = input("\n是否包含子目录? (y/n, 默认 n): ").strip().lower()
            include_subdir = (subdir_choice == 'y')
            process_directory(os.path.dirname(os.path.abspath(__file__)), include_subdir)
            input("\n按回车键返回主菜单...")

        elif choice == "3":
            custom_dir = input("\n请输入要扫描的目录绝对路径 (或直接拖拽文件夹到此窗口): ").strip()
            custom_dir = custom_dir.strip('"').strip("'")

            if os.path.exists(custom_dir):
                subdir_choice = input("是否包含子目录? (y/n, 默认 n): ").strip().lower()
                include_subdir = (subdir_choice == 'y')
                process_directory(custom_dir, include_subdir)
            else:
                print(f"\n[!] 错误: 找不到目录 -> {custom_dir}")

            input("\n按回车键返回主菜单...")

        elif choice == "4":
            process_directory(log_dir, include_subdir=True, only_response_dir=True)
            input("\n按回车键返回主菜单...")

        elif choice == "0":
            print("\n[*] 已退出。")
            break
        else:
            print("\n[!] 无效输入，请重新输入。")
            time.sleep(1)


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n[*] 用户中断，已退出。")
    except Exception as e:
        print(f"\n[!] 发生致命错误: {e}")
        input("\n按回车键退出...")
