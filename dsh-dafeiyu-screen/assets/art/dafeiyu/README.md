# 大肥鱼图片素材

`source-images.tar.xz` 随插件发布，包含原始 60 帧、水平平板 60 帧、背景、参考图、GIF 和原素材记录。帧按 RGBA PAM 保存后整体无损压缩，透明度和每个像素均与原 PNG 一致；恢复 PNG 后文件编码与 SHA-256 可能不同。归档内的 manifest 保留原始 PNG 校验记录。

运行直接使用包内已合成的视频，无需解压。需要编辑素材时，从插件目录运行以下命令（仅需 Python，无第三方库；输出目录必须尚不存在）：

```powershell
python scripts/unpack_art.py --output restored-art
```

两组序列为 1664×1024、60 帧、30 FPS。原始序列位于解压目录的 `original/frames`；当前使用的水平平板序列位于 `horizontal-tablet/frames`。

重新生成视频时，`python scripts/build_media.py` 自动读取包内归档和 `assets/background.png`，需要 PATH 中有 FFmpeg。可用 `--ffmpeg` 指定可执行文件。默认素材路径与运行时当前目录无关。

原始角色和背景由用户提供，水平平板版本在此基础上局部编辑。素材权利见 [第三方说明](../../../THIRD_PARTY.md)。
