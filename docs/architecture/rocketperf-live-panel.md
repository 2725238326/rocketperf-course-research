# rocketperf 架构 live panel

**位置**：[rocketperf-live-panel.html](rocketperf-live-panel.html)（本目录），双击在浏览器无限循环播放（30 秒/循环）；也可截图/录屏用于PPT。配置源为 [rocketperf-live-panel.config.json](rocketperf-live-panel.config.json)。

**生成方式**：基于开源 [live-panel-skill](https://github.com/ythx-101/live-panel-skill)（MIT）。内容维护在 config JSON（结构见其 `references/config-schema.md`），改后运行 `python tools/livepanel_inject.py` 重新注入生成 HTML。

## 面板内容口径

- **主线四层**：入口层 → thermo（NASA9/九气相HP）∥ nozzle（L0/冻结流）→ cycle（开式/补燃）→ 输出与验证
- **Isp 仪表盘**（喷管框内）：归档结果切换 — 单室甲烷 324.4 / RP-1 310.6 / GG 整机 296.3 / ORSC 整机 291.1 s
- **循环情景**（cycle 框内）：GG 开式外排与 ORSC 富氧补燃交替显示，run log 同步滚动
- **右侧验证支路**：regime 域评估 / study 参数扫描 / 治理归档，三个独立入口按序点亮
- **底部口径行**：守恒账（质量·元素·焓·轴功）+ 越域拒算不外推 + 失败不写结果；不含运行计数
- **连线语义标签**：h·元素库存、T0·P0·几何、平衡态、出口流、F·Isp·残差

数字均为归档事实（`deliverables/ppt-materials/*.csv`，可用 `python tools/demo_data.py --check` 复算），不虚构成递增。

## Windows 渲染说明

skill 原脚本仅支持 Linux/macOS（Chrome DevTools pipe 需要 POSIX fd 传递）。本机通过给 `livepanel.py` 打 Windows 桥接补丁（HTTP 端口 + 标准库 WebSocket 客户端）跑通 `check_frames.py`（124时间点0布局问题）。mp4 需另装 ffmpeg 后用 `render.py` 生成。

## 维护

- 改内容：编辑 config.json，运行 `python tools/livepanel_inject.py` 注入；改机器/布局后浏览器打开用 `__check()` 自检
- 架构事实与 `project/modules.json` 登记一致；模块依赖、归档结果变更时同步更新面板
