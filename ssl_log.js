console.log("[*] 正在初始化 Hook 模块...");

function getRealPackageName() {
    try {
        var libc = Process.getModuleByName("libc.so");
        var fopen = new NativeFunction(libc.findExportByName("fopen"), 'pointer', ['pointer', 'pointer']);
        var fgets = new NativeFunction(libc.findExportByName("fgets"), 'pointer', ['pointer', 'int', 'pointer']);
        var fclose = new NativeFunction(libc.findExportByName("fclose"), 'int', ['pointer']);

        var path = Memory.allocUtf8String("/proc/self/cmdline");
        var mode = Memory.allocUtf8String("r");
        var fp = fopen(path, mode);
        if (!fp.isNull()) {
            var buf = Memory.alloc(256);
            fgets(buf, 256, fp);
            fclose(fp);
            var pkg = buf.readUtf8String().trim();
            if (pkg) return pkg;
        }
    } catch (e) {}
    return Process.name || "Gadget";
}

send({
    type: 'init',
    package_name: getRealPackageName()
});

var hookedAddresses = new Set();

function hookSSL(libName) {
    try {
        var mod = Process.getModuleByName(libName);
        if (!mod) return;
        var writeAddr = mod.findExportByName('SSL_write');
        var readAddr = mod.findExportByName('SSL_read');

        // --- Hook SSL_write (发往服务器) ---
        if (writeAddr && !hookedAddresses.has(writeAddr.toString())) {
            hookedAddresses.add(writeAddr.toString());
            Interceptor.attach(writeAddr, {
                onEnter: function(args) {
                    var sslPtr = args[0].toString();
                    var buf = args[1];
                    var len = args[2].toInt32();
                    
                    if (len > 0 && len < 10 * 1024 * 1024) {
                        try {
                            // 尝试匹配请求头，将 Accept-Encoding: 等长替换为无效头 X-Ignore-Encode:
                            // 保持总字节数严格不变，防止破坏 C 层调用栈返回值校验
                            var previewLen = Math.min(len, 4096);
                            var headerStr = buf.readUtf8String(previewLen);
                            if (headerStr && headerStr.indexOf("Accept-Encoding:") !== -1) {
                                var patchedHeader = headerStr.replace(/Accept-Encoding:/gi, "X-Ignore-Encode:");
                                if (patchedHeader.length === headerStr.length) {
                                    buf.writeUtf8String(patchedHeader);
                                }
                            }
                        } catch (e) {}

                        try {
                            var rawBytes = buf.readByteArray(len);
                            if (rawBytes) {
                                send({
                                    type: 'data',
                                    direction: 'REQ',
                                    ssl_id: sslPtr
                                }, rawBytes);
                            }
                        } catch (e) {}
                    }
                }
            });
        }

        // --- Hook SSL_read (服务器返回) ---
        if (readAddr && !hookedAddresses.has(readAddr.toString())) {
            hookedAddresses.add(readAddr.toString());
            Interceptor.attach(readAddr, {
                onEnter: function(args) {
                    this.sslPtr = args[0].toString();
                    this.buf = args[1];
                },
                onLeave: function(retval) {
                    var len = retval.toInt32();
                    if (len > 0 && len < 10 * 1024 * 1024) {
                        try {
                            var rawBytes = this.buf.readByteArray(len);
                            if (rawBytes) {
                                send({
                                    type: 'data',
                                    direction: 'RES',
                                    ssl_id: this.sslPtr
                                }, rawBytes);
                            }
                        } catch (e) {}
                    }
                }
            });
        }
    } catch (e) {}
}

// 优先 Hook 目标库
var priorityLibs = ['libcocos2dcpp.so', 'libssl.so'];
priorityLibs.forEach(hookSSL);

// 查漏补缺
Process.enumerateModules().forEach(function(mod) {
    var nameLower = mod.name.toLowerCase();
    if (nameLower.indexOf('ssl') !== -1 || nameLower.indexOf('crypto') !== -1 || nameLower.indexOf('cronet') !== -1) {
        hookSSL(mod.name);
    }
});

console.log("[+] 全局 Hook 挂载完毕，请操作应用。");