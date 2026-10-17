# 报告插图

本报告共使用十二张插图：七张科研与计算流程图、一张动态架构图和四张 GUI 页面。科研图按正文使用 SVG 矢量格式排版，并提供 PDF 与 450 dpi PNG 版本。

| 正文图号 | 内容与条件 | 文件 |
|---|---|---|
| 图 4-1 | 动态架构在 24 s 的静态取帧；完整展示见配套 HTML | [PNG](fig08_dynamic_architecture.png) · [动态页面](architecture-report.html) |
| 图 5-1 | 五类计算入口、求解分支与结果输出流程 | [PNG](fig01_calculation_flow.png) · [SVG](fig01_calculation_flow.svg) · [PDF](fig01_calculation_flow.pdf) |
| 图 6-1 | GUI 燃烧室：液态 CH₄/O₂，10 MPa，O/F=0.9，石墨活度约 1.09 | [PNG](fig09_gui_combustion.png) |
| 图 6-2 | GUI 推进剂比较：O/F=2.6，Pc=10 MPa，At=0.01 m²，面积比 10，真空 | [PNG](fig10_gui_propellant.png) |
| 图 6-3 | GUI 喷管：甲烷 O/F=2.6，面积比 40，海平面背压；附液体 HP 域评估 | [PNG](fig11_gui_nozzle.png) |
| 图 6-4 | GUI 循环：长十乙一级背景的 RP-1 富氧补燃研究情景 | [PNG](fig12_gui_cycle-orsc.png) |
| 图 7-1 | 液体 CH₄/O₂ 燃烧温度、特征速度和富燃侧石墨活度 | [PNG](fig02_chamber_tradeoff.png) · [SVG](fig02_chamber_tradeoff.svg) · [PDF](fig02_chamber_tradeoff.pdf) |
| 图 7-2 | 甲烷与固定 RP-1 方法比较；共同几何，各自入口定义 | [PNG](fig03_propellant_comparison.png) · [SVG](fig03_propellant_comparison.svg) · [PDF](fig03_propellant_comparison.pdf) |
| 图 7-3 | 甲烷喷管面积比、真空比冲与出口面积关系 | [PNG](fig04_nozzle_tradeoff.png) · [SVG](fig04_nozzle_tradeoff.svg) · [PDF](fig04_nozzle_tradeoff.pdf) |
| 图 7-4 | 甲烷单室背压响应与理想出口压力 | [PNG](fig05_backpressure_domain.png) · [SVG](fig05_backpressure_domain.svg) · [PDF](fig05_backpressure_domain.pdf) |
| 图 7-5 | 甲烷和氧入口升温相对于基线的变化 | [PNG](fig07_inlet_response.png) · [SVG](fig07_inlet_response.svg) · [PDF](fig07_inlet_response.pdf) |
| 图 7-6 | 开式甲烷与富氧补燃 RP-1 情景的质量流路和推力收支 | [PNG](fig06_cycle_comparison.png) · [SVG](fig06_cycle_comparison.svg) · [PDF](fig06_cycle_comparison.pdf) |

科研图由保存的 C 计算结果绘制。图中离散点按计算网格显示；插值、统计误差带和实测数据不在本报告范围内。各图的输入条件、来源文件和图像校验值见[数据清单](../data/manifest.json)与[图表清单](figure-manifest.json)。

动态架构页面采用 MIT 许可的 live-panel-skill 渲染器，报告同时提供静态取帧与可播放的 [HTML 页面](architecture-report.html)。GUI 截图展示程序界面和计算诊断；定量分析见正文第 7 节。
