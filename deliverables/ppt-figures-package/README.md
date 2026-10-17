# PPT 图表包 · 使用说明

所有图统一风格：浅色底、模板蓝 `#1f4e9c` 主色、微软雅黑，SVG 矢量可无损缩放，PNG 1600×900、200 dpi，拉伸到半页幻灯片仍清晰。数据全部来自归档结果（`deliverables/ppt-materials/*.csv`），来源可用 `python tools/demo_data.py --check` 复算。

## architecture/ · 架构图（SVG，直接插入或另存为图片）

| 文件 | 建议用法 |
|---|---|
| assignment.svg | 作业总览：三项要求的方法、结果与未覆盖（1920×1080，可整页） |
| business.svg | 业务层次：应用用例 → 领域模型 → 基础设施 |
| components.svg | 模块架构：6 模块三层结构与依赖，标注行数 |
| workflow.svg | 工作流程：七步，每步产物 / 模块 / 失败处理 |
| report-flow.svg | 计算流程：GB/T 1526 符号，含失败出口与独立命令 |

SVG 插入 PPT：PowerPoint 里"插入 → 图片"直接选 `.svg`，可任意缩放；若版本不支持，用浏览器打开截图。

## code-graph.html · C 代码关系（交互图）

双击打开。只含 `src/` 与 `include/` 的 56 个 C 文件和 139 条 `#include` 依赖，按模块分色，方块是 `.c`、圆角是 `.h`。拖动节点、滚轮缩放、点击高亮一个文件的全部关联、右上角按文件名筛选。生成数据的表头不计入。由 `python tools/code_graph.py` 从源码重新提取。

## charts/ · 计算结果图（PNG，1600×900，透明底）

| 文件 | 内容 | 对应页 |
|---|---|---|
| p6-cstar.png | c* 随 O/F 变化，标注 c* 峰与温度峰 | P6 燃烧室 |
| p7-propellants.png | 甲烷 vs RP-1：Isp、c* 成对柱状 | P7 推进剂对比 |
| p8-isp-epsilon.png | 真空比冲随面积比 ε 变化 | P8 喷管 |
| p9-ambient.png | ε10/ε40 真空 vs 海平面；ε40 海平面过膨胀拒算（不填假值） | P9 环境对照 |
| p10-cycle.png | GG 开式 vs ORSC 补燃：推力、整机比冲 | P10 循环 |
| p17-backpressure.png | 四背压系列比冲曲线，空缺=拒算 | P17 备答 |

透明底 PNG 放在浅色模板上直接用；若模板页有图片背景，先加白底。

## rocketperf-live-panel.html · 架构动画（答辩演示）

双击在浏览器全屏循环播放（30 秒/循环），也可录屏插入 PPT。详细内容与维护见同目录 `live-panel-说明.md`。要点：
- 主线四层依次运转：入口 → thermo（HP 平衡）∥ nozzle（冻结膨胀）→ cycle（轴功闭合）→ 输出验证
- 喷管框内 Isp 仪表盘：归档结果间切换（甲烷 324.4 / RP-1 310.6 / 整机 296.3 / 291.1 s）
- 循环框内 GG/ORSC 两情景交替，run log 同步滚动
- 右侧独立入口（regime / study / 治理归档）按序点亮
- 底部为守恒账（质量·元素·焓·轴功）与"失败不写结果"，无运行计数

改内容：编辑 `rocketperf-live-panel.config.json`（本包内副本），在项目里运行 `python tools/livepanel_inject.py` 重新注入。

## 复核

- 架构图：`python tools/render_architecture.py`、`python tools/report_flow.py` 生成；`python tools/project.py check` 校验
- 图表：`python tools/ppt_figures.py` 重新生成；`python tools/demo_data.py --check` 复算数据
