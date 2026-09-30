# 大肥鱼图片素材

本目录保存循环动画所需的原始与修订素材，独立于插件安装包。两组帧均为 1664×1024 透明 RGBA PNG；按 `frame_000.png` 到 `frame_059.png` 以 30 FPS 播放，时长 2 秒，末帧后直接返回首帧。

| 目录 / 文件 | 内容 |
| --- | --- |
| `background/room.png` | 用户提供的白色房间背景，保留原文件像素 |
| `original/frames/` | 原始摇尾序列，60 帧，平板倾斜 |
| `horizontal-tablet/frames/` | 水平平板修订序列，60 帧，当前插件使用 |
| `horizontal-tablet/edit-reference.png` | AI 局部编辑的基准图，供后续修订参考 |
| `horizontal-tablet/PROCESSING-NOTES.md` | 平板处理方式、文字安全区与验证记录 |
| `previews/horizontal-tablet.gif` | 缩小后的棋盘背景动画预览；GIF 时间精度有限，以 PNG 序列和 MP4 为准 |
| `manifest.json` | 每张图片的大小、SHA-256，以及输入 ZIP 的校验值 |

首帧预览：

![水平平板透明首帧](horizontal-tablet/frames/frame_000.png)

最终合成的静态预览和 MP4 / WebM / H.264 位于 [`../../dsh-dafeiyu-screen/assets/`](../../dsh-dafeiyu-screen/assets/)。原始 ZIP 的 PNG 已无损解包，避免再提交相同素材的压缩副本。

## 重新合成

从仓库根目录运行（需要 Python 和支持 libx264、libvpx-vp9 的 FFmpeg）：

```powershell
python dsh-dafeiyu-screen/scripts/build_media.py --frames art/dafeiyu/horizontal-tablet/frames --background art/dafeiyu/background/room.png --ffmpeg C:/path/to/ffmpeg.exe
```

省略 `--ffmpeg` 时沿用本机 KANALI 安装目录中的 FFmpeg。构建脚本也支持输入原始 ZIP。目录输入的校验值按帧序号依次拼接 ASCII 文件名与文件字节后计算 SHA-256；单张素材的校验值见 `manifest.json`。

## 素材权利

原始角色和背景由用户提供；水平平板版本在此基础上局部编辑。代码的 MIT 许可证不自动覆盖这些素材的再分发或商业授权，详见 [`THIRD_PARTY.md`](../../dsh-dafeiyu-screen/THIRD_PARTY.md)。
