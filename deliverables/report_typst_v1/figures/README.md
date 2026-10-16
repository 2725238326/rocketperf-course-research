# 报告插图索引

报告共使用十二张插图：原有七张科研与计算流程图、一张动态架构取帧，以及四张实际 GUI 页面截图。七张原图使用白底、统一字体、克制配色与清晰单位，正文插入 SVG 矢量版本；另提供嵌字体 PDF 和 450 dpi PNG。SVG 中文文字已转路径，可在缺少字体的机器查看。动态架构与 GUI 作为程序展示单独列示。

| 正文图号 | 内容与条件 | 可用格式 |
|---|---|---|
| 图 4-1 | 动态架构在 24 s 的静态取帧；单室与循环示例值随时间切换，不表示一次实时求解 | [PNG](fig08_dynamic_architecture.png) · [配套动态 HTML](architecture-report.html) |
| 图 5-1 | 五类独立计算入口、求解分支和失败契约 | [PNG](fig01_calculation_flow.png) · [SVG](fig01_calculation_flow.svg) · [PDF](fig01_calculation_flow.pdf) |
| 图 6-1 | GUI 燃烧室：液态 CH₄/O₂，10 MPa，O/F=0.9，石墨活度约 1.09，返回越域 | [PNG](fig09_gui_combustion.png) |
| 图 6-2 | GUI 推进剂比较：共同 O/F=2.6、Pc=10 MPa、At=0.01 m²、面积比 10、真空 | [PNG](fig10_gui_propellant.png) |
| 图 6-3 | GUI 喷管：甲烷 O/F=2.6、面积比 40、海平面，附着求解拒绝；液体 HP 域评估另列 | [PNG](fig11_gui_nozzle.png) |
| 图 6-4 | GUI 循环：长十乙一级背景的 RP-1 富氧补燃研究情景，涡轮出口压力求得约 17.95 MPa | [PNG](fig12_gui_cycle-orsc.png) |
| 图 7-1 | 液体 CH₄/O₂，10 MPa，120/100 K：温度、c* 与富燃侧石墨判据 | [PNG](fig02_chamber_tradeoff.png) · [SVG](fig02_chamber_tradeoff.svg) · [PDF](fig02_chamber_tradeoff.pdf) |
| 图 7-2 | 甲烷/固定 RP-1，共同 Pc、At、面积比、背压、质量 O/F；各自入口保留 | [PNG](fig03_propellant_comparison.png) · [SVG](fig03_propellant_comparison.svg) · [PDF](fig03_propellant_comparison.pdf) |
| 图 7-3 | 甲烷单室 O/F=2.6，真空面积比与出口面积代价 | [PNG](fig04_nozzle_tradeoff.png) · [SVG](fig04_nozzle_tradeoff.svg) · [PDF](fig04_nozzle_tradeoff.pdf) |
| 图 7-4 | 同一甲烷单室工况，背压下的成功结果和理想出口压力；拒绝点不补零 | [PNG](fig05_backpressure_domain.png) · [SVG](fig05_backpressure_domain.svg) · [PDF](fig05_backpressure_domain.pdf) |
| 图 7-5 | O/F=3.4，甲烷 120→140 K、氧 100→110 K 的差值，不计供给能耗/压降/相变 | [PNG](fig07_inlet_response.png) · [SVG](fig07_inlet_response.svg) · [PDF](fig07_inlet_response.pdf) |
| 图 7-6 | 开式甲烷与富氧补燃 RP-1 研究情景，外排/回流及总消耗，不作循环排名 | [PNG](fig06_cycle_comparison.png) · [SVG](fig06_cycle_comparison.svg) · [PDF](fig06_cycle_comparison.pdf) |

文件编号用于主题身份，正文图号由 Typst 按章节和出现次序生成，两者不强行一致。

## 动态架构与 GUI 来源

[动态架构原页](../../../docs/architecture/rocketperf-live-panel.html)是说明性演示，数值取自既有归档，渲染器基于 [live-panel-skill](https://github.com/ythx-101/live-panel-skill)，随附[原 MIT 许可](architecture-LICENSE-MIT.txt)。配套 `architecture-report.html` 为报告冻结副本，适配 Windows 字体、文字对比度、两处图框高度及标题分隔线位置，保留原内容与演示时序。脚本在 0—30 s 的 121 个时间点检查布局，并在 4、14、24 s 取帧，选用文字已完整显示的 24 s 画面；PNG 为 2400×3000。HTML 可以独立播放，PDF 内的本地链接指向这份配套文件。

原 `deliverables/gui-shots/` 是此前保存的截图，其中循环页包含未完成的数值动画，且历史说明曾将该文件误认成开式工况。原件保持不变，报告改用实际 GUI 工作树 `feature/gui` 的页面资源与 C 桥接程序重新取图。四页均采用 1920×1080 CSS 视口、2 倍像素密度、减少动态效果设置，等待 C 调用完成后保存为 3840×2160 PNG，未改写页面数值。循环页四个主要数值与该次 C 返回逐项核对。构建、页面源码、工况和图像哈希见[展示图清单](report-visuals-manifest.json)。

`fig12_gui_cycle-orsc.png` 明确表示富氧补燃情景。GUI 喷管页的匹配面积比约 10.91 属于液体 HP 冻结喷管；正文独立定比热诊断的约 9.92 来自另一组输入，二者分别标注。截图用于说明操作与反馈，报告定量结论仍使用保存的 C 结果。

数据来源及精度见[数据清单](../data/manifest.json)，逐图文件哈希见[图表清单](figure-manifest.json)。[绘图脚本](build_figures.py)读取保存的 C 输出，只有排版、单位显示和差值绘图，不包含物理解算。循环标注也从保存的质量及推力账读取。

[展示图脚本](build_report_visuals.py)默认从冻结 HTML 重取架构图并校验保存的 GUI 图。只有显式传入 `--refresh-architecture` 才从原页更新报告动画；需要重新取 GUI 图时，还需传入真实 GUI 工作树与 C 桥接程序路径，具体命令见上级 README。

预期拒绝点保留原因，不伪装成有效曲线；离散网格峰值不当作连续最优值。所有曲线都属于报告声明的研究输入，不能替代真实型号的实测性能图。
