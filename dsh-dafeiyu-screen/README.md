# PANORAMA-360-SE-DSH-PET

Windows 展域 360 SE（PASE，USB 391a:1021）屏幕桌宠插件。白色房间背景铺满 2240×1080；大肥鱼原比例、上下贴边，以 30 FPS、60 帧、2 秒视频循环播放。手持平板上的真实余额独立更新，主数字字号 68。USB 保活失败后自动重连，恢复当前素材和最新余额。

## 在 DSH 官方“添加插件”窗口安装

可直接填写以下任意一种来源，无需先运行本项目安装脚本：

- GitHub：`https://github.com/Andromedahk/PANORAMA-360-SE-DSH-PET.git`
- 本地仓库根目录：`D:/codex/鼠标垫支架/kanali-open-screen`
- 解压后的插件目录（包含 package.json）；原 `dsh-dafeiyu-screen` 子目录也支持。

安装后启用 **PANORAMA-360-SE-DSH-PET**，在插件配置页打开控制台。DSH 负责安装 YAML 等 npm 依赖；首次显示时插件自动检查并下载 Python，用户无需预装 Python 或运行 CMD。

仓库为公开仓库，可直接使用上述 GitHub 地址安装，无需私有仓库访问权限。选择 npm 镜像只影响 npm 依赖，GitHub 下载仍需要网络能够访问 GitHub。

`panorama-360-se-dsh-pet` 是包标识，目前未发布到 npm 注册表，不能只填写该包名安装。可直接使用 GitHub 地址或本地目录安装。

升级请按 DSH 提示先卸载旧版，再安装新版；旧版 `dsh-dafeiyu-screen` 与新插件不要同时启用。用户数据保留在原数据目录。

## 从零安装

1. 下载并解压 `PANORAMA-360-SE-DSH-PET-1.1.1-windows-x64.zip` 到可写文件夹。
2. 双击 `安装到DSH.cmd`。脚本按 `dependencies.json` 检查 Node、Python、npm 包和 DSH；缺失时自动下载到用户目录，不需要管理员权限。
3. 在 DSH 插件页启用 **PANORAMA-360-SE-DSH-PET**。已有旧版 `dsh-dafeiyu-screen` 时，先停用旧版，避免占用同一控制台端口。
4. 退出 KANALI，连接 USB，在插件控制台点击“开始显示”。默认读取 DSH 登录账户；也可保存 DeepSeek API Key。

没有 DSH 时安装器会通过 npm 安装依赖表固定版本的 DSH CLI。要打开其 Web 界面，可使用安装输出的 dsh 路径执行 `web --profile desktop`。DSH 桌面应用不是必需依赖，也不会被自动替换。

只使用独立 GUI：双击 `启动PANORAMA.cmd`，缺少依赖时自动准备。控制台默认 `http://127.0.0.1:18432/`。第一次准备 Python 可能需要等待网络下载；失败会显示可重试错误。

已安装 DSH 的用户也可从插件页选择本地 `.tgz` 包，或执行：

```powershell
dsh plugin --profile desktop add file:C:/path/panorama-360-se-dsh-pet-1.1.1.tgz
```

## 依赖与缓存

[DEPENDENCIES.md](DEPENDENCIES.md) 是说明表，[dependencies.json](dependencies.json) 是安装器实际读取的固定版本、地址与 SHA-256 清单。运行时只有 YAML 一个 npm 依赖，Python 只使用标准库；无需 pip、FFmpeg、KANALI 或替换 USB 驱动。

Node/Python/DSH 不放入插件包，默认缓存到 `%LOCALAPPDATA%/PANORAMA-360-SE-DSH-PET/runtimes`；通过 `PANORAMA_RUNTIME_HOME` 可指定缓存目录。优先复用兼容的已安装 Node/Python。下载失败可重试，校验失败不会执行；多个安装进程使用互斥锁防止同时解压。

为保留旧版本的设置、余额 Key 和原屏幕备份，数据目录继续使用 `%LOCALAPPDATA%/DSHDaFeiYuScreen`。Key 使用 Windows DPAPI 加密，不能复制到其他账户直接使用。日志不记录 Key；USB 只发送视频和显示文字。

## 显示与重连

余额默认每 30 秒刷新，可设为 10–3600 秒。失败保留最后余额并标记 STALE。正常更新仅发送文字，不切换或重新上传视频。USB 暂时断开后重连间隔由 2 秒递增至 30 秒；素材已在屏幕中时复用。点击“停止连接”会取消自动重连。恢复原显示会应用首次启用前的配置和文字布局。

关闭网页不会停止后台；独立控制台使用“退出控制台”退出，DSH 模式停用插件即可释放进程和 USB。

## 构建、测试、发布

```powershell
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/dependencies.ps1 -Component Node
npm ci --ignore-scripts
npm test
python tests/test_reconnect.py
powershell -NoProfile -ExecutionPolicy Bypass -File scripts/package.ps1
```

从帧序列重建素材才需要 FFmpeg：

```powershell
python scripts/build_media.py --frames ../art/dafeiyu/horizontal-tablet/frames --ffmpeg C:/path/ffmpeg.exe
```

默认背景是 `assets/background.png`，与验收画面一致。依赖安装器不自动下载仅供开发的 FFmpeg。精简发布包包含代码、依赖清单及成片，不含运行环境、node_modules、原始 60 张帧或下载缓存。

支持范围：Windows 10/11 x64、已实测的 PASE 屏幕。首次安装需要可访问 nodejs.org、python.org 和 npm 注册表。真实断电、面板亮度与播放流畅度仍需实体屏幕验收。

协议与插件代码 MIT；角色素材权利单独见 [THIRD_PARTY.md](THIRD_PARTY.md)。
