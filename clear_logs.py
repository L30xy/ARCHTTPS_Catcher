import os
import stat
import shutil
import configparser
import time


def get_target_dir():
    """读取配置文件获取真实的存储路径，并校验路径安全性"""
    base_work_dir = os.path.abspath(os.path.dirname(__file__))
    ini_path = os.path.join(base_work_dir, 'config.ini')
    dir_name = 'arc_logs'

    if os.path.exists(ini_path):
        config = configparser.ConfigParser()
        config.read(ini_path, encoding='utf-8')
        dir_name = config.get('output', 'output_dir', fallback='arc_logs').strip()
    else:
        print("[-] 找不到 config.ini，默认使用 'arc_logs' 目录。")

    target_path = os.path.abspath(os.path.join(base_work_dir, dir_name))
    return target_path, base_work_dir


def remove_readonly(func, path, excinfo):
    """清除只读属性并重试删除的回调函数"""
    try:
        os.chmod(path, stat.S_IWRITE | stat.S_IREAD)
        func(path)
    except Exception:
        pass


def safe_force_delete(directory, base_work_dir):
    """安全且强制地解除文件只读占用并删除目标文件夹"""
    if not os.path.exists(directory):
        return True

    # 安全护栏：禁止删除当前工作目录本身、系统根目录或磁盘根目录
    if directory == base_work_dir or len(os.path.splitdrive(directory)[1]) <= 3:
        print(f"[!] 安全拦截：目标路径 '{directory}' 为工作根目录或系统盘符，拒绝执行删除！")
        return False

    print("[*] 正在清理目标目录...")
    try:
        shutil.rmtree(directory, onerror=remove_readonly)
    except Exception as e:
        print(f"[-] 删除过程中发生异常: {e}")

    return not os.path.exists(directory)


def main():
    target_dir, base_work_dir = get_target_dir()

    print("====================================================")
    print("               抓包记录清理工具")
    print("====================================================")
    print("请将该脚本与start.bat置于同一目录")
    print(f"[*] 当前配置的存储路径为:\n    {target_dir}")

    if not os.path.exists(target_dir):
        print("\n[OK] 该目录不存在，无需清理。")
        input("\n按回车键退出...")
        return

    # 统计大小和文件数
    total_size = 0
    file_count = 0
    for root, dirs, files in os.walk(target_dir):
        for f in files:
            fp = os.path.join(root, f)
            if not os.path.islink(fp):
                try:
                    total_size += os.path.getsize(fp)
                    file_count += 1
                except OSError:
                    pass

    size_mb = total_size / (1024 * 1024)

    print(f"[*] 共发现 {file_count} 个文件，占用空间 {size_mb:.2f} MB")
    print("----------------------------------------------------")
    print("⚠️ 警告：此操作将不可恢复地删除上述所有文件！")
    print("⚠️ 请确保当前的抓包脚本 (start.bat) 已经停止运行！")
    print("----------------------------------------------------")

    confirm = input("确认要清空所有抓包记录吗？(输入 y 确认，其他任意键取消): ").strip().lower()

    if confirm != 'y':
        print("\n[*] 操作已取消。")
        time.sleep(1)
        return

    if safe_force_delete(target_dir, base_work_dir):
        os.makedirs(target_dir, exist_ok=True)
        print("[+] 清理成功！所有记录已删除并重建空目录。")
    else:
        print("\n[!] 删除失败！")
        print("[!] 请检查是否有其他程序（如：Frida 抓包窗口、编辑器、文件资源管理器）正在占用该文件夹内的文件。")

    input("\n按回车键退出...")


if __name__ == "__main__":
    main()
