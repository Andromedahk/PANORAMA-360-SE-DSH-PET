# 第三方与素材说明

- 屏幕协议及 Windows USB 客户端来自本项目 `kanali-open-screen`。其开源依据为 [DXVSI/Tryx-Linux-GUI](https://github.com/DXVSI/Tryx-Linux-GUI)，MIT；已保留 Fadli Arsani、DXVSI 的版权与许可证于 `LICENSE` 和 `worker/LICENSE`。
- DSH 插件依据 [deepseek-ai/deepseek-harness](https://github.com/deepseek-ai/deepseek-harness) 官方文档与公开服务接口独立实现。未打包整个 DSH。
- YAML 解析器 `yaml` 2.8.1：ISC，见依赖包内 LICENSE。
- Windows 嵌入式 Python 3.10.11，来源 `https://www.python.org/ftp/python/3.10.11/python-3.10.11-embed-amd64.zip`，完整许可证见 `bin/python/LICENSE.txt`。
- 便携包内 Node.js 24.19.0，完整许可证见 `runtime/LICENSE`；npm 插件包不携带 Node。
- FFmpeg 仅用于本机构建视频，不分发 FFmpeg 程序。
- 大肥鱼 60 帧序列和白色房间背景由用户提供。合成输出沿用原素材权利状态，**不自动授予第三方 MIT 素材授权**；再分发或商业使用这些视觉素材应由素材权利方决定。源文件校验值见 `assets/media.json`。

- 1.0.4 的水平平板为基于用户原始帧的 AI 局部编辑，统一应用于全部 60 帧；脸部、尾巴动画及改动区域之外的像素保留原素材。
