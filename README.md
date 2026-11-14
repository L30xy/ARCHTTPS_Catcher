# ARCHTTPS_Catcher
这是一个基于 `Frida Gadget` 和 `Zygisk` 注入的高级 Android HTTPS 明文抓包工具。通过直接 Hook 底层的 `SSL_read` 和 `SSL_write` 函数，彻底绕过应用层的 SSL Pinning（证书绑定）校验。
