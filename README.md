# Arcaea HTTPS 抓包工具 (基于 Frida Gadget)

这是一个基于 `Frida Gadget` 和 `Zygisk` 注入的 Android HTTPS 明文抓包工具。通过直接 Hook 底层的 `SSL_read` 和 `SSL_write` 函数，彻底绕过应用层的 SSL Pinning（证书绑定）校验。

本项目特别针对基于 Cocos2d-x 引擎的音游（如 Arcaea）进行了深度优化，解决了多线程并发串包、分片传输（Chunked）、Gzip 压缩丢失等痛点问题。

## ✨ 核心特性

* **底层明文拦截**：绕过常规 HTTPS 抓包限制，无视自签名证书和防抓包检测。

* **连接级并发隔离**：基于 `SSL*` 指针严格隔离并发网络请求，避免高并发下的数据串包和损坏。

* **无损报文修改**：通过等长替换 `Accept-Encoding` 头部，强制要求服务器返回明文，而不破坏 C 层底层的内存与网络状态机。

* **高效二进制传输**：摒弃低效的 Base64 转换，使用 Frida 原生二进制通道回传数据，大幅提升性能。

* **全套辅助工具**：内置一键启动、配置修改、端口重置、日志清理、JSON 格式化提取等自动化脚本。

## 📦 环境要求

### 1. 电脑端 (PC)

* **操作系统**：Windows 10 / 11

* **环境依赖**：Python 3.10+

* **核心模块**：安装依赖 `pip install -r requirements.txt` (必须为 `frida==17.5.2`)

* **ADB 工具**：需安装 Android Platform-Tools 并配置环境变量。

### 2. 手机端 (Android)

* **系统要求**：Android 9+

* **Root 环境**：Magisk / KernelSU / APatch

* **Zygisk 环境**：推荐使用 Zygisk Next

* **注入模块**：[zygisk-gadget-stealth v1.0.1](https://github.com/hex91/zygisk-gadget-stealth)

  * 模块配置：设置模式为 `mode=listen`，端口设为 `27052` (推荐与电脑端一致)。

  * 白名单配置：将需要抓包的 App 包名加入模块的白名单列表中。

## 📂 项目结构与重命名指南

为了保证工具链的正常运行，**部分核心文件不能重命名**。

### ❌ 核心文件（不可改名）

* `config.ini`：核心配置文件，所有脚本均依赖此文件读取路径和参数。

* `ssl_log.js`：Frida 注入核心脚本，由 Python 自动读取。

* `run_ssl.py`：Python 数据接收与解析引擎，由一键启动脚本调用。

* `requirements.txt`：Python 依赖列表。

### ✅ 独立辅助脚本（可自由加前缀或改名）

以下文件主要方便手动操作，你可以自由修改文件名（如改为 `1_一键启动.bat`）：

* `start.bat`：一键清理环境、映射端口并启动抓包。

* `change_settings.bat`：图形化的 CLI 配置文件修改器。

* `reset_port.bat`：用于重置或修复 ADB 端口转发的急救脚本。

* `clear_logs.py`：安全解除文件占用并清空历史抓包记录的工具。

* `format_json.py`：JSON 提取与格式化工具（支持拖拽文件/文件夹批量处理）。

## 🚀 快速开始

### 抓包步骤

0. 先行配置 Android 端与 Windows 端环境。

1. 将手机通过 USB 连接至电脑，并开启“USB 调试”。

2. 在手机上启动目标 App，并使其保持在后台运行。

3. 在电脑端双击运行 `start.bat`。

4. 终端提示“附加成功！等待网络数据...”后，在手机上操作 App 触发网络请求。

5. 所有抓取到的数据将自动按 `包名/域名_请求类型/路由_时间戳` 的结构，保存在 `arc_logs/` 目录中。

6. 抓包结束后，在命令窗口按下 `Ctrl+C` 安全停止并保存残余数据。

### 工具链使用提示

* **想修改存储路径或端口？**
  双击运行 `change_settings.bat` 即可可视化修改。

* **生成的 txt 文件太乱想提取 JSON？**
  将生成的 `.txt` 抓包文件（或整个文件夹）直接拖拽到 `format_json.py` 图标上，即可自动剥离 HTTP 头并生成美化后的 `.json` 文件。

* **ADB 连接不上或端口被占用？**
  拔插手机后，双击运行 `reset_port.bat` 即可一键恢复。

## ⚠️ 声明与注意事项

1. **仅供学习与安全研究使用**：请勿将本工具用于任何非法破解、黑产获利或侵犯他人隐私的用途。使用者因使用本工具引发的任何纠纷与法律责任由使用者自行承担。

2. **Frida 版本匹配**：电脑端的 `frida` 版本必须与手机端的 `frida-gadget` 版本**严格一致**（本项目标配为 `17.5.2`），否则会导致注入失败或 App 闪退。

3. **私有协议限制**：本工具针对标准 HTTPS (TLS/SSL) 协议。如果目标 App 使用了完全自研的私有加密协议而非 OpenSSL/BoringSSL 库，可能无法抓取明文。

4. **Vibe Coding 说明**：部分代码由 Deepseek V4.1 Flash 与 Gemini 4 Argon 模型生成或编辑优化。
