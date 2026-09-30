# Open Screen · 展域 360 SE

独立的 Windows USB 屏幕内容传输工具，MIT 开源原型。适用于已实测的 **TRYX 展域 / PANORAMA 360 SE，USB `391a:1021`（RK PASE）**。

## 已完成的实机验证

- Windows 自带 `usbprint` 驱动直接双向通信，不需要 KANALI 运行，也不需要更换 USB 驱动。
- 读取型号、固件版本、素材目录及当前显示配置。
- 将 PNG 转为 2240 × 1080 H.264，分块上传并切换显示。
- 测试图大小 323,797 字节，分为 262,144 和 61,653 字节两块；开始、每块和结束均收到成功响应。
- 用户已确认实体屏幕显示 `OPEN SCREEN` 和四色条正常。
- 测试完成后已恢复原素材选择和显示配置，并通过设备回读验证。
- 实测设备固件：`v2.0.5.20260403`，设备应用：`v2.0.1.20260416`。

这次没有安装 USBPcap，也没有截获原 KANALI 进程的流量：协议参考已有 MIT 开源实现，随后通过本机独立客户端的真实 USB 收发与实体显示验证。`captures/` 保存的是本工具的收发内容。

## 使用

1. 从系统托盘完全退出 KANALI。
2. 双击 **启动屏幕工具.cmd**。
3. 点击“选择文件”，然后点击“发送到屏幕”。
4. 保持窗口打开可通过 Ping 维持屏幕连接。重新使用 KANALI 前先关闭本工具。

需要 Windows、带 Tkinter 的 Python 3.10+、提供 `libx264` 的 FFmpeg。本机这些条件已经具备。优先使用 PATH 中的 FFmpeg；本机回退使用 KANALI 安装目录中已有的 FFmpeg。项目不附带 KANALI 程序、DLL、媒体或固件；在另一台电脑独立部署时请自行安装 FFmpeg。

图片按比例完整放入画面，多余部分填黑；图片转换成 60 秒、30 fps 的 H.264 片段。支持选择 PNG/JPG/BMP/WebP、GIF、MP4/MKV/AVI/MOV/WebM。**静态 PNG 已实机验证，其他格式和长视频尚未实机验证。** 当前只提供整屏播放；未实现分屏、指标面板、实时桌面镜像或固件更新。

“恢复测试前画面”使用本机 `captures/before-test-config.bin`，恢复原素材选择和显示设置。它不删除上传的测试素材，也不能恢复 KANALI 运行时的动态指标叠加；如需动态指标，请重新启动 KANALI。

## 命令行

在本目录运行：

```powershell
python -X utf8 screen.py devices
python -X utf8 screen.py info
python -X utf8 screen.py catalog
python -X utf8 screen.py prepare "D:\图片\wallpaper.png"
python -X utf8 screen.py send "D:\图片\wallpaper.png"
python -X utf8 screen.py restore "captures\before-test-config.bin"
python -X utf8 -m unittest -v
```

可用 `--ffmpeg "D:\ffmpeg\bin\ffmpeg.exe"` 指定转换工具。命令行完成后释放连接，不提供持续保活；长期使用请打开窗口版。

## 通信记录

每次连接在 `captures/时间-随机号/` 下生成日志：

- `events.jsonl`：方向、时间、长度和对应文件。
- `*-out.bin`、`*-in.bin`：实际发出的帧和实际读到的字节。
- `previous-config.bin`：切换前的配置；窗口版另存每次上传前配置。

离线解码，不连接屏幕：

```powershell
python -X utf8 inspect_capture.py "captures\20260930-035439-db56dc"
```

抓取中可能包含本机设备标识、素材名及完整图像内容，已默认排除在 Git 之外。窗口空闲保活不写逐包日志，避免长期产生大量文件。

## 源码

- `winusbprint.py`：Windows 设备发现、重叠读写、超时取消和单实例占用。
- `protocol.py`：TRYX 帧与最小 Protobuf 编解码，保留配置中的未知字段。
- `screen.py`：设备查询、转换、上传、切换与恢复。
- `gui.py`：中文桌面窗口，单工作线程串行操作设备。
- `inspect_capture.py`：本地收发记录解码。
- `PROTOCOL.md`：通信协议与验证边界。

当前是可运行原型，没有打包安装程序，也没有发布到公开仓库。断连或确认超时不会自动重传；失败后先读取设备状态再决定下一步，不能把“已经发送”当作“已经成功”。

## 来源与授权

协议参考 [DXVSI/Tryx-Linux-GUI](https://github.com/DXVSI/Tryx-Linux-GUI)，MIT，固定参考提交 `4f1d9e591e2db6c3b2b4c13b56f38c64f942f5b6`。参见 `THIRD_PARTY.md` 和 `LICENSE`。Windows 传输和 Python 客户端在本项目实现。
## 大肥鱼 DSH 插件

新增 [大肥鱼 · 展域屏](dsh-dafeiyu-screen/README.md)：2240×1080 摇尾动画循环、独立余额更新、DSH 插件和 Windows 图形控制台。视频已经合成为 30 FPS、60 帧、2 秒；余额变化不会重传或切换视频。

原始帧、水平平板版帧、背景和动画预览已整理到 [图片素材目录](art/dafeiyu/README.md)，包含全部 120 张透明帧、素材校验清单和重新合成方法。
