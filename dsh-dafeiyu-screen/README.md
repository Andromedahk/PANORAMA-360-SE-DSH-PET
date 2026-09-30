# 大肥鱼 · 展域屏

Windows 上的 DeepSeek Harness（DSH）插件，也可独立打开图形控制台。为 TRYX 展域 360 SE / PASE（USB `391a:1021`）显示摇尾大肥鱼，并定期更新人民币余额。

![动画背景预览](assets/preview.jpg)

## 直接使用

1. 解压 Windows 便携包，双击 **启动大肥鱼.cmd**。不要只拷贝一个文件，保留整个文件夹。
2. 从托盘完全退出 KANALI、Open Screen 等其他屏幕工具。
3. 点击 **开始显示**。视频只需上传一次，之后余额更新只发送独立文字，不会反复切换视频。
4. 默认每 30 秒查询余额，可改为 10–3600 秒；可以开启“控制台或 DSH 插件启动后自动显示”。这不是 Windows 开机自启。

控制台地址：<http://127.0.0.1:18432/>。独立控制台与 DSH 插件共用设置，并只能运行一个后台。重复启动会打开已有控制台。

关闭网页不会停止后台；独立运行时点击 **退出控制台** 完全退出。DSH 模式下，由 DSH 插件的启停管理后台。**停止连接**释放 USB 并暂停轮询，屏幕是否待机由原配置决定；**恢复原显示**恢复首次启用前的素材选择与文字布局，再释放连接。

## 安装到 DSH

本项目是原生 Cordis 插件，包含 `apply(ctx)`、`dsh.bundle`、`cordis.patch.yml` 和 `./client` 浏览器模块；不是仅有提示词的 skill。

双击 **安装到DSH.cmd**，默认安装到本机 `desktop` profile。也可用官方 CLI：

```powershell
dsh plugin --profile desktop add file:C:/path/to/dsh-dafeiyu-screen
```

在 DSH 的插件页找到 **dsh-dafeiyu-screen**，进入插件详情即可打开控制台。DSH Web 本机页面支持嵌入控制台；桌面版提供“打开独立控制台”入口，以适配桌面应用的页面隔离策略。安装后如当前窗口尚未出现入口，重新加载 DSH。

使用打包文件时：

```powershell
dsh plugin --profile desktop add ./dsh-dafeiyu-screen-1.0.4.tgz
```

移除：

```powershell
dsh plugin --profile desktop remove dsh-dafeiyu-screen
```

该插件应在连接 USB 的 Windows 主机上运行。远端 Linux/SSH 主机不能直接驱动本地水冷屏。

## 余额与凭证

- DSH 模式优先通过官方 `ctx.deepseekAccount.getBalance()` 读取已登录账号，汇总人民币充值钱包与赠送钱包。
- 独立模式读取 `DSH_HOME/.credentials.yaml`，默认 `%USERPROFILE%/.dsh/.credentials.yaml` 的版本 1 格式；也支持环境变量 `DAFEIYU_API_KEY`、`DSHPET_KEY`、`DEEPSEEK_API_KEY`。
- GUI 中保存的 API Key 优先级最高，只请求官方 `https://api.deepseek.com/user/balance`。由 Windows DPAPI 按当前用户加密，不能直接拷贝到别的账号使用。
- 凭证仅在主机侧使用，不写入视频、不发送给屏幕、不返回网页，也不记录到日志。插件不发起模型推理，不模拟消费、不充值。
- 网络或认证失败时保留最后一次成功余额，屏幕标记 `STALE`，界面显示原因。没有成功读数时显示 `--`，不会把失败伪装成余额为零。
- 余额变化只走已实测的文字更新指令。默认 30 秒查询一次，失败逐步退避，HTTP 429 尊重服务器重试间隔。

## 素材与布局

完整可编辑素材见仓库中的 [`art/dafeiyu`](../art/dafeiyu/README.md)：原始 60 帧、水平平板 60 帧、背景、编辑基准图和预览；这些原始素材不放入插件安装包。

- 用户提供的 `frame_000.png`–`frame_059.png` 以 30 FPS 顺序合成，恰好 2 秒、60 帧，不复制结束帧。
- 背景等比填充至 2240×1080，裁掉上下多余区域；角色缩放至 1722×1060 像素，按全部 60 帧的可见轮廓水平居中，上下各留 10 像素，保留尾巴全部摆动范围；比初版放大约 23%。
- 角色手中平板的黑色区域显示人民币余额、币种与更新时间，角色整体居中。数字保持水平，使用设备已支持的文字层；不宣称支持平板角度的透视旋转。屏幕字体使用已验证的 `roboto-regular`，避免中文字体缺失。
- `assets/tail-swing.webm` 用于浏览器兼容预览；`assets/tail-swing.mp4` 可直接播放；`assets/tail-swing.h264` 是设备上传格式。`assets/media.json` 保存尺寸、帧数与原始素材 SHA-256。
- 没有切换“待机/受击”等多段视频。本版本持续播放同一段素材；首次启用或恢复原素材仍可能闪一下。真实屏幕的循环接缝与实际呈现帧率留待人工观察。

## 数据位置与故障处理

设置、Windows 加密凭证、原显示备份和 USB 调试记录位于 `%LOCALAPPDATA%/DSHDaFeiYuScreen`，可用 `DAFEIYU_HOME` 覆盖。便携包、npm 包及 Git 均不携带这些个人数据。

- “另一个 Open Screen 实例正在使用屏幕”：关闭其他屏幕控制软件，再点开始。
- USB 拔出后会显示连接异常；重新插入后点击开始显示。
- 忘记退出独立控制台会使 DSH 插件无法占用 18432 端口。在已有控制台点退出，再重新启用插件。
- 余额来源变化：移除 GUI 保存的 Key 后重新读取 DSH 账号；账号切换期间可点停止，再开始。
- 该版本只接受实测 PASE 产品，不会更换驱动、刷固件或操作其他 USB 设备。

## 开发与验证

Node.js 22.19+；源码运行还需 Windows Python 3.10+，或先运行 `scripts/package.ps1` 下载官方嵌入式 Python。便携包已附 Node 和 Python，不依赖系统 PATH。源码依赖安装与测试：

```powershell
npm ci
npm test
python -m unittest discover -s tests -p "test_*.py"
```

重新合成（需要 FFmpeg）：

```powershell
python scripts/build_media.py --frames ../art/dafeiyu/horizontal-tablet/frames --background ../art/dafeiyu/background/room.png --ffmpeg C:/path/ffmpeg.exe
```

`scripts/hardware-smoke.js` 是显式实体设备测试：先停止控制台连接，再运行；它短暂显示测试数字、读取设备确认，最后恢复原显示。普通自动测试不访问 USB，也不读取真实余额。

开发依据为官方仓库 2026-09-30 的 `639ed015397290b3745d163aafe02ffee4aa3f84`：

- [插件打包与安装](https://github.com/deepseek-ai/deepseek-harness/blob/639ed015397290b3745d163aafe02ffee4aa3f84/docs/user/develop/basic/publish.md)
- [Cordis 生命周期](https://github.com/deepseek-ai/deepseek-harness/blob/639ed015397290b3745d163aafe02ffee4aa3f84/docs/cordis-tutorial/02-lifecycle-and-effects.md)
- [账号余额服务](https://github.com/deepseek-ai/deepseek-harness/blob/639ed015397290b3745d163aafe02ffee4aa3f84/packages/credentials/deepseek-account/src/index.ts)
- [插件页面插槽](https://github.com/deepseek-ai/deepseek-harness/blob/639ed015397290b3745d163aafe02ffee4aa3f84/packages/client/ui-plugin-manager/src/client/slot-contract.ts)

详细检查记录见 [VALIDATION.md](VALIDATION.md)。源代码采用 MIT；用户提供的角色与背景素材单独列于 [THIRD_PARTY.md](THIRD_PARTY.md)，不以代码许可证代替素材授权。

## 更新记录

- **1.0.4 · 2026-09-30**：将角色手持平板调整为水平，60 帧使用一致的局部修订；重新合成居中放大的循环视频，并将余额与更新时间居中放入新平板。

- **1.0.3 · 2026-09-30**：角色与平板余额整体居中，放大约 23%，高度占屏幕约 98%；同步放大平板数字和网页预览。

- **1.0.2 · 2026-09-30**：余额移至角色手持平板，独立更新白色数字；添加 WebM 网页预览；修复重新连接时上一会话残留数据造成的握手失败。

- **1.0.0 · 2026-09-30**：合成 2 秒摇尾视频；新增 DSH 原生插件、Windows 图形控制台、真实余额定时更新、失败状态、加密 API Key、显示恢复和便携包。
