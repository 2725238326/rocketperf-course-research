# 072：报告补入动态架构与 GUI 页面并润色语言

日期：2026-10-16。任务：DOC-006。用户要求把动态架构图、实际 GUI 页面纳入课程报告，修正循环工况说明，并继续优化报告语言与版式。

## 本轮变更

- 报告正文为 [report.typ](../deliverables/report_typst_v1/report.typ)，重新编译为 [report-v1.pdf](../deliverables/report_typst_v1/report-v1.pdf)。PDF 仍使用已核实的 MIT 许可 Typst 报告模板，没有补填学校、班级、学号或教师信息。
- 第 4.4 节新增动态架构运行展示；第 6.4 节新增 GUI 页面与操作示例。动态 HTML 的 24 s 静态取帧进入 PDF，冻结可播放副本为 `deliverables/report_typst_v1/figures/architecture-report.html`，其 MIT 许可副本为 `architecture-LICENSE-MIT.txt`。
- 动态架构取帧源为 `docs/architecture/rocketperf-live-panel.html`，脚本在 0—30 s 以 121 个时间点做布局检查，并在 4、14、24 s 取 QA 帧；报告选用文字已完成显示的 24 s 帧。对报告副本只调整 Windows 字体、次要文字对比度、两处六行图框高度和标题分隔线位置，未改模块内容、示例数据或动画时序。
- `fig09_gui_combustion.png` 展示液态 CH₄/O₂、O/F=0.9 的石墨判据拒算；`fig10_gui_propellant.png` 展示共同 O/F=2.6 的甲烷/RP-1 比较；`fig11_gui_nozzle.png` 展示甲烷 O/F=2.6、面积比 40、海平面背压下的附着拒算与域评估；`fig12_gui_cycle-orsc.png` 明确展示长十乙一级背景的 RP-1 富氧补燃研究情景。
- GUI 图由 `feature/gui` 工作树的页面资源、本地 C 桥接程序和减少动态效果设置重新取图，CSS 视口 1920×1080、设备像素比 2，所得 PNG 为 3840×2160。截图脚本等待 C 调用完成；循环页的 285.50 kN、291.13 s、3.376 MW、17.95 MPa 与 C 返回逐项比对。旧 `deliverables/gui-shots/` 原件未改写。
- 摘要、研究目标、计算方法、参数边界、程序设计、算例结果和结论均做了语言润色，减少重复否定句和审查式短句，保留研究数值、引用、模型身份与适用范围。
- 更新 `figures/README.md`、报告 README 和 DOC-006 任务契约，明确 GUI 为界面展示证据，不替代保存的 C 计算结果，也不构成发动机试验验证。

## 复核结果

- Typst 0.14.2 编译成功；仅保留上游 `mitex:0.2.5` 的 `kai` 弃用警告。当前 PDF 为 A4、22 页。
- `build/report-qa/doc006/review_report.py` 使用 `pypdf` 核对：22 页、摘要和十个正文要求章节、六位组员姓名、79 个 PDF 链接标注、8 个外部网址；报告源码原有 199 个不同数值标记均保留，未出现 TODO/FIXME/占位文本。
- 22 页全部通过 `pdftoppm` 渲染，并查看封面、目录、摘要、方法、参数、动态架构页、流程图、GUI 两页、全部结果图表、结论、参考文献和分工页。未发现图像裁切、文字溢出、表格越界、孤立标题、空白页或页码错位。GUI 文字在正文插图尺寸下仍可识别；动态架构图的 121 个时间点布局检查均为空。
- `python tools/project.py check`：PASS。首轮 `python tools/quality.py` 曾因 taskshot 尚未创建而报告一条断链，补齐本记录后重新执行。
- taskshot 补齐后重新执行 `python tools/quality.py`：PASS，六组检查（project、governance、debug、release、runner、handoff）全部通过；最新报告保存在 `build/quality/latest.json`。报告改动后未沿用旧 DOC-005 证据。

## 边界与保留项

- 动态面板的单室、循环和验证示例值来自不同归档状态，是运行结构展示，不是一次实时求解的时间历史。
- GUI 页面显示 C 核心的操作反馈和当前输入；报告第 7 节的定量结论仍来自保存的研究 JSON/C 输出。固定 RP-1、绝热循环、历史给定热状态循环和定比热域诊断继续保持独立身份。
- 未修改原始课件、原始来源、原 Markdown 报告、PPT、旧 GUI 截图和旧科研图；未重新检索网页，也未把界面截图写成实机性能或独立实验。
