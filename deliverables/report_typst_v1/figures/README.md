# 科研图索引

七张图使用白底、统一字体、克制配色与清晰单位，避免双纵轴、装饰背景和伪造误差带。PDF 正文插入 SVG 矢量版本；另提供嵌字体 PDF 及 450 dpi PNG。SVG 中文文字已转路径，可在缺少字体的机器查看。

| 正文图号 | 内容与条件 | 可用格式 |
|---|---|---|
| 图 5-1 | 五类独立计算入口、求解分支和失败契约 | [PNG](fig01_calculation_flow.png) · [SVG](fig01_calculation_flow.svg) · [PDF](fig01_calculation_flow.pdf) |
| 图 7-1 | 液体 CH₄/O₂，10 MPa，120/100 K：温度、c* 与富燃侧石墨判据 | [PNG](fig02_chamber_tradeoff.png) · [SVG](fig02_chamber_tradeoff.svg) · [PDF](fig02_chamber_tradeoff.pdf) |
| 图 7-2 | 甲烷/固定 RP-1，共同 Pc、At、面积比、背压、质量 O/F；各自入口保留 | [PNG](fig03_propellant_comparison.png) · [SVG](fig03_propellant_comparison.svg) · [PDF](fig03_propellant_comparison.pdf) |
| 图 7-3 | 甲烷单室 O/F=2.6，真空面积比与出口面积代价 | [PNG](fig04_nozzle_tradeoff.png) · [SVG](fig04_nozzle_tradeoff.svg) · [PDF](fig04_nozzle_tradeoff.pdf) |
| 图 7-4 | 同一甲烷单室工况，背压下的成功结果和理想出口压力；拒绝点不补零 | [PNG](fig05_backpressure_domain.png) · [SVG](fig05_backpressure_domain.svg) · [PDF](fig05_backpressure_domain.pdf) |
| 图 7-5 | O/F=3.4，甲烷 120→140 K、氧 100→110 K 的差值，不计供给能耗/压降/相变 | [PNG](fig07_inlet_response.png) · [SVG](fig07_inlet_response.svg) · [PDF](fig07_inlet_response.pdf) |
| 图 7-6 | 开式甲烷与富氧补燃 RP-1 研究情景，外排/回流及总消耗，不作循环排名 | [PNG](fig06_cycle_comparison.png) · [SVG](fig06_cycle_comparison.svg) · [PDF](fig06_cycle_comparison.pdf) |

文件编号用于主题身份，正文图号由 Typst 按章节和出现次序生成，两者不强行一致。

数据来源及精度见[数据清单](../data/manifest.json)，逐图文件哈希见[图表清单](figure-manifest.json)。[绘图脚本](build_figures.py)读取保存的 C 输出，只有排版、单位显示和差值绘图，不包含物理解算。循环标注也从保存的质量及推力账读取。

预期拒绝点保留原因，不伪装成有效曲线；离散网格峰值不当作连续最优值。所有曲线都属于报告声明的研究输入，不能替代真实型号的实测性能图。
