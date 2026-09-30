# 依赖表

安装器读取同目录 `dependencies.json`。以下固定版本已配置下载与校验，不在发布包内预装。

| 组件 | 版本/要求 | 获取方式 | 用途 |
|---|---|---|---|
| Windows | 10/11 x64 | 操作系统自带 | PowerShell 5.1、DPAPI、usbprint |
| Node.js | 最低 22.19；下载 24.21.0 | nodejs.org 官方 ZIP，固定 SHA-256 | DSH / 独立 GUI |
| Python | 最低 3.10 x64；下载 3.13.7 | python.org 官方嵌入包，固定 SHA-256 | USB 通信；仅标准库 |
| yaml | 2.8.1 | npm，shrinkwrap 完整性锁定 | DSH 本地凭证格式解析 |
| DSH CLI | 已安装则复用；缺失下载 0.2.0-rc.2 | npm 官方 @deepseek-ai/dsh | 宿主，仅 DSH 模式需要 |
| FFmpeg | 开发工具 | 构建者自行指定 | 仅重制视频；用户播放无需安装 |

`安装到DSH.cmd` 准备全部必需依赖并执行 DSH 插件安装；`启动PANORAMA.cmd` 准备 Node/npm 依赖，首次访问通信功能时自动准备 Python。

可单独运行 `scripts/dependencies.ps1 -Component Python` 或 `Node`、`App`、`DSH`、`All`。`-ForceDownload -CacheRoot <新目录>` 用于绕过系统运行环境、验证全新下载；不会卸载现有软件或改系统 PATH。

下载缓存可以复用；离线且无缓存无法完成首次安装。失败信息会保留，重新运行即可重试。缓存包先校验再解压，损坏旧目录重命名保留。

参考：[DSH 官方文档](https://deepseek-harness.github.io/deepseek-harness/)、[Node 版本及校验](https://nodejs.org/dist/v24.21.0/SHASUMS256.txt)、[Python 3.13.7](https://www.python.org/downloads/release/python-3137/)。
