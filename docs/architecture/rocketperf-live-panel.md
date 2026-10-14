# rocketperf 架构 live panel

**用途**：答辩用代码架构动画面板，双击 `rocketperf-live-panel.html` 在浏览器无限循环播放；也可截图/录屏用于PPT。

**生成方式**：基于开源 [live-panel-skill](https://github.com/ythx-101/live-panel-skill)（MIT）。内容维护在 `rocketperf-live-panel.config.json`（结构见其 `references/config-schema.md`），改后重新注入模板生成 HTML。

## 面板内容口径

- **主线四层**：入口层 → thermo（NASA9/九气相HP）∥ nozzle（L0/冻结流）→ cycle（开式/补燃）→ 输出与验证
- **右侧验证支路**：regime 域评估 / study 参数扫描 / 治理归档，三个独立入口按序点亮
- **连线语义标签**：h·元素库存、T0·P0·几何、平衡态、出口流、F·Isp·残差
- **数字来源**：13772项检查、57张CEA卡、ΔT≈0.0044K（HP口径）均为归档事实，静态显示不虚构成递增；credit行写明来源

## Windows 渲染说明

skill 原脚本仅支持 Linux/macOS（Chrome DevTools pipe 需要 POSIX fd 传递）。本机通过给 `livepanel.py` 打 Windows 桥接补丁（HTTP 端口 + 标准库 WebSocket 客户端）跑通 `check_frames.py`（124时间点0布局问题）。mp4 需另装 ffmpeg 后用 `render.py` 生成。

## 维护

- 改内容：编辑 config.json 后用模板 `<!--LIVE_CONFIG-->` 注入点重新生成 HTML（skill 的 scaffold/check_frames 流程）
- 架构事实与 `project/modules.json` 登记一致；模块依赖、验证数字变更时同步更新面板
