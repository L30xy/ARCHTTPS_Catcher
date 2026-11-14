import frida
import sys
import datetime
import os
import re
import json
import configparser
import time
import gzip
import zlib
from collections import defaultdict, deque

# 全局配置与状态
BASE_DIR = "arc_logs"
current_pkg = "unknown"
INI_CONF = None
SAVE_RES_HEADER = True

# 按 SSL 连接指针隔离请求队列与响应缓冲
REQ_QUEUES = defaultdict(deque)  # ssl_id -> deque of req_meta
RES_BUFFERS = {}                 # ssl_id -> dict of response buffer state


def load_ini_config():
    global BASE_DIR, INI_CONF, SAVE_RES_HEADER
    config = configparser.ConfigParser()
    if os.path.exists('config.ini'):
        config.read('config.ini', encoding='utf-8')
    INI_CONF = config
    BASE_DIR = config.get('output', 'output_dir', fallback='arc_logs')
    SAVE_RES_HEADER = config.getboolean('output', 'save_response_header', fallback=False)


def clean_domain(domain):
    return re.sub(r'[\\/*?:"<>|]', "_", domain.replace(':', '_'))


def get_unique_filepath(filepath):
    if not os.path.exists(filepath):
        return filepath
    base_path, ext = os.path.splitext(filepath)
    counter = 1
    new_filepath = f"{base_path}_{counter}{ext}"
    while os.path.exists(new_filepath):
        counter += 1
        new_filepath = f"{base_path}_{counter}{ext}"
    return new_filepath


def decode_chunked_bytes(raw_bytes):
    """标准 HTTP Chunked 字节流解码，返回 (decoded_bytes, is_complete)"""
    pos = 0
    out = bytearray()
    total_len = len(raw_bytes)
    while pos < total_len:
        line_end = raw_bytes.find(b'\r\n', pos)
        if line_end == -1:
            return bytes(out), False
        size_line = raw_bytes[pos:line_end].split(b';')[0].strip()
        try:
            chunk_size = int(size_line, 16)
        except ValueError:
            # 非法 chunk 头，回退返回原数据
            return raw_bytes, True

        if chunk_size == 0:
            return bytes(out), True

        chunk_start = line_end + 2
        chunk_end = chunk_start + chunk_size
        if chunk_end + 2 > total_len:
            return bytes(out), False

        out.extend(raw_bytes[chunk_start:chunk_end])
        pos = chunk_end + 2

    return bytes(out), False


def parse_and_flush_response(ssl_id, force=False):
    """检查当前 ssl_id 的响应缓冲区是否接收完毕，若完毕则解压并落盘"""
    if ssl_id not in RES_BUFFERS:
        return

    state = RES_BUFFERS[ssl_id]
    buf = state["buffer"]

    if not state["header_parsed"]:
        sep_idx = buf.find(b'\r\n\r\n')
        if sep_idx == -1:
            if force and len(buf) > 500:
                save_res_file(state, bytes(buf))
                del RES_BUFFERS[ssl_id]
            return

        header_bytes = bytes(buf[:sep_idx])
        state["header_text"] = header_bytes.decode('utf-8', errors='replace')
        state["body_start"] = sep_idx + 4
        state["header_parsed"] = True

        # 解析关键响应头
        headers_lower = state["header_text"].lower()
        cl_match = re.search(r'content-length:\s*(\d+)', headers_lower)
        if cl_match:
            state["content_length"] = int(cl_match.group(1))
        if 'transfer-encoding: chunked' in headers_lower:
            state["is_chunked"] = True
        if 'content-encoding: gzip' in headers_lower:
            state["encoding"] = 'gzip'
        elif 'content-encoding: deflate' in headers_lower:
            state["encoding"] = 'deflate'

    body_bytes = bytes(buf[state["body_start"]:])
    is_complete = False

    if state["is_chunked"]:
        decoded_body, is_complete = decode_chunked_bytes(body_bytes)
        if is_complete or force:
            body_bytes = decoded_body
    elif state["content_length"] is not None:
        if len(body_bytes) >= state["content_length"]:
            body_bytes = body_bytes[:state["content_length"]]
            is_complete = True
    else:
        # 无明确长度标识时，尝试判断是否为完整 JSON
        try:
            test_str = body_bytes.decode('utf-8').strip()
            if (test_str.startswith('{') and test_str.endswith('}')) or \
               (test_str.startswith('[') and test_str.endswith(']')):
                json.loads(test_str)
                is_complete = True
        except Exception:
            pass

    if is_complete or force:
        save_res_file(state, body_bytes)
        del RES_BUFFERS[ssl_id]


def save_res_file(state, body_bytes):
    if not body_bytes and not state["header_text"]:
        return

    # 处理压缩格式 (Gzip / Deflate)
    if state.get("encoding") == 'gzip' or body_bytes.startswith(b'\x1f\x8b'):
        try:
            body_bytes = gzip.decompress(body_bytes)
        except Exception:
            pass
    elif state.get("encoding") == 'deflate':
        try:
            body_bytes = zlib.decompress(body_bytes)
        except Exception:
            pass

    body_text = body_bytes.decode('utf-8', errors='replace').strip()
    if not body_text and not SAVE_RES_HEADER:
        return

    # 如果是合法 JSON 则美化或规范化格式
    try:
        parsed_json = json.loads(body_text)
        body_text = json.dumps(parsed_json, ensure_ascii=False, indent=2)
    except Exception:
        pass

    host = state.get("req_host", "unknown_host")
    full_route = state.get("full_route", "unknown")
    time_str = state.get("time_str", datetime.datetime.now().strftime("%H%M%S"))

    clean_route = re.sub(r'[^a-zA-Z0-9_]', '_', full_route.split('?')[0]).strip('_') or "root"
    save_dir = os.path.join(BASE_DIR, current_pkg, f"{host}_response")
    os.makedirs(save_dir, exist_ok=True)

    if SAVE_RES_HEADER and state.get("header_text"):
        final_content = state["header_text"] + "\r\n\r\n" + body_text
        filename = f"{clean_route}_{time_str}.txt"
    else:
        final_content = body_text
        filename = f"{clean_route}_{time_str}.json"

    filepath = get_unique_filepath(os.path.join(save_dir, filename))
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(final_content)

    print(f"[RES] {full_route}\n  -> {os.path.basename(filepath)}\n  -> 目录: {save_dir}\n", flush=True)


def handle_request(ssl_id, raw_bytes, time_str):
    content = raw_bytes.decode('utf-8', errors='replace')
    first_line = content.split('\n', 1)[0].strip()

    # 识别是否为 HTTP 请求头起始包
    http_methods = ('GET ', 'POST ', 'PUT ', 'DELETE ', 'HEAD ', 'OPTIONS ', 'PATCH ')
    if first_line.startswith(http_methods):
        host_match = re.search(r'Host:\s*([^\r\n]+)', content, re.IGNORECASE)
        domain = clean_domain(host_match.group(1).strip() if host_match else "unknown_host")
        parts = first_line.split(' ')
        method = parts[0] if len(parts) >= 1 else "REQ"
        full_route = parts[1] if len(parts) >= 2 else "unknown"

        clean_route = re.sub(r'[^a-zA-Z0-9_]', '_', full_route.split('?')[0]).strip('_') or "root"
        filename = f"{method}_{clean_route}_{time_str}.txt"
        save_dir = os.path.join(BASE_DIR, current_pkg, f"{domain}_log")
        os.makedirs(save_dir, exist_ok=True)
        filepath = get_unique_filepath(os.path.join(save_dir, filename))

        with open(filepath, "w", encoding="utf-8") as f:
            f.write(content)

        REQ_QUEUES[ssl_id].append({
            "host": domain,
            "full_route": full_route,
            "time_str": time_str,
            "filepath": filepath
        })
        if len(REQ_QUEUES[ssl_id]) > 50:
            REQ_QUEUES[ssl_id].popleft()

        print(f"[REQ] {full_route}\n  -> {os.path.basename(filepath)}\n  -> 目录: {save_dir}\n", flush=True)
    else:
        # 可能是分片发送的 Request Body，追加到该连接最近的一个请求文件中
        if REQ_QUEUES[ssl_id]:
            last_req = REQ_QUEUES[ssl_id][-1]
            try:
                with open(last_req["filepath"], "a", encoding="utf-8") as f:
                    f.write(content)
            except Exception:
                pass


def handle_response(ssl_id, raw_bytes, time_str):
    if raw_bytes.startswith(b"HTTP/"):
        # 如果该连接上有未完成的旧响应，强制刷盘
        if ssl_id in RES_BUFFERS:
            parse_and_flush_response(ssl_id, force=True)

        req_meta = REQ_QUEUES[ssl_id].popleft() if REQ_QUEUES[ssl_id] else {
            "host": "unknown_host",
            "full_route": "orphan_response",
            "time_str": time_str
        }

        RES_BUFFERS[ssl_id] = {
            "buffer": bytearray(raw_bytes),
            "header_parsed": False,
            "header_text": "",
            "body_start": 0,
            "content_length": None,
            "is_chunked": False,
            "encoding": None,
            "req_host": req_meta["host"],
            "full_route": req_meta["full_route"],
            "time_str": req_meta["time_str"]
        }
    else:
        if ssl_id in RES_BUFFERS:
            RES_BUFFERS[ssl_id]["buffer"].extend(raw_bytes)
        else:
            # 过滤小于 500 字节的无头底层心跳分片
            if len(raw_bytes) < 500:
                return
            RES_BUFFERS[ssl_id] = {
                "buffer": bytearray(b"HTTP/1.1 200 OK\r\n\r\n" + raw_bytes),
                "header_parsed": False,
                "header_text": "",
                "body_start": 0,
                "content_length": None,
                "is_chunked": False,
                "encoding": None,
                "req_host": "unknown_host",
                "full_route": "orphan_fragment",
                "time_str": time_str
            }

    parse_and_flush_response(ssl_id, force=False)


def on_message(message, data):
    global current_pkg
    if message['type'] != 'send':
        return
    payload = message.get('payload')
    if not isinstance(payload, dict):
        return

    msg_type = payload.get('type')
    if msg_type == 'init':
        pkg_name = payload.get('package_name', '')
        host_port = INI_CONF.get('frida', 'host', fallback='127.0.0.1:27052')
        current_pkg = pkg_name if pkg_name and pkg_name.lower() != 'gadget' else f"port_{host_port.split(':')[-1]}"
        print(f"\n[*] 目标包名: {current_pkg}\n", flush=True)
        return

    if msg_type == 'data' and data:
        direction = payload.get('direction')
        ssl_id = payload.get('ssl_id', 'default_ssl')
        time_str = datetime.datetime.now().strftime("%H%M%S")

        if direction == 'REQ':
            handle_request(ssl_id, data, time_str)
        elif direction == 'RES':
            handle_response(ssl_id, data, time_str)


if __name__ == "__main__":
    load_ini_config()
    host = INI_CONF.get('frida', 'host', fallback='127.0.0.1:27052')
    gadget = INI_CONF.get('frida', 'gadget_name', fallback='Gadget')

    print(f"[*] 等待目标 App 启动 (地址: {host}, 进程标识: {gadget}) ...")

    session = None
    while session is None:
        try:
            device = frida.get_device_manager().add_remote_device(host)
            session = device.attach(gadget)
            print("[*] 附加成功！正在注入抓包脚本...")
        except Exception:
            time.sleep(0.5)

    with open('ssl_log.js', 'r', encoding='utf-8') as f:
        script = session.create_script(f.read())
    script.on('message', on_message)
    script.load()
    print("[*] 抓包模块加载完毕！请操作应用，按 Ctrl+C 停止并保存缓存。")
    try:
        sys.stdin.read()
    except KeyboardInterrupt:
        print("\n[*] 正在将残余缓冲区数据刷入磁盘...")
        for sid in list(RES_BUFFERS.keys()):
            parse_and_flush_response(sid, force=True)
        print("[+] 已安全退出。")