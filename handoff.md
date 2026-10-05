# 项目交接

接手先读[当前工作面](worknow.md)，运行`python tools/project.py doctor`。任务状态由登记生成；分支、提交和工作树以Git实况为准，不在这里重复维护测试数量。

## 现在有什么

- C17：定比热教学喷管、十物种NASA9、九种中性C/H/O气体TP/HP（气态温度/显式焓或固定液态反应物锚点）、冻结/固定面积喷管、给定热状态外排循环及单输入扫描。入口扩展只闭合燃烧室和单喷管，不改循环。
- 固定参考：NASA9/Cantera软件对照、四个CEA受限气相方法工况、合成循环实际六状态CEA TP、五状态主室冻结喷管与11个固定面积C点、泵/涡轮解析极限。没有完整发动机独立实验或整机循环同条件外部参考。
- 新气态研究：12组入口温度/O-F条件的HP和固定喷管响应，每组新跑CEA；见[结果与SVG](docs/adiabatic-inlet-study.md)。它不是液态预热或两型实装设计。
- 入口候选：[RES-006](调研/专题/RES-006_液态与煤油入口.md)锁定三份CEA单温度反应物锚点、CoolProp 7.1.0 EOS身份和NIST surrogate原文/摩尔分数；[数据](data/parameters/feed_property_candidates.json)含11条事实/未知记录。仅CH₄(L)/O₂(L)两条固定记录已提取为C常量，见[21次C/6次CEA方法验证](docs/liquid-anchor-validation.md)；候选JSON、EOS、RP-1/surrogate不作生产运行时输入。
- 连续液体：[RES-007](调研/专题/RES-007_连续液体基准.md)固定407节点/700内部点及饱和、理想项参考；[C17查表](docs/liquid-feed-validation.md)独立返回CH4/O2密度与化学焓；ANA-010已将查表入口焓/C-H-O库存接入九气相HP和固定面积冻结喷管，见[核验说明](docs/liquid-combustion-validation.md)。运行时不依赖CoolProp，温压仍是研究假设；泵升压、喷注、分流轴功和完整循环未闭合。
- 工程：模块依赖、严格输入、不可变构建、失败运行记录、统一验收和固定提交交接。成功结果还要通过关系复算，不能只凭JSON可解析或数值为正。

先看[作业对接总览与三视图](docs/architecture/README.md)。模型限制看[热化学/喷管](docs/thermo-nozzle-validation.md)与[循环](docs/cycle-validation.md)。研究结果看[改进与代价](docs/improvement-analysis.md)、[实际状态参考](docs/research-reference-coverage.md)和[入口焓/热边界](docs/research-thermal-boundary.md)，保存文件从[研究归档](results/research/README.md)进入。

## 怎么复跑

```powershell
python tools/project.py check
python tools/quality.py
python tools/pipeline.py run --model prescribed-cycle --case cases/benchmarks/prescribed_cycle.ini
python tools/pipeline.py run --case cases/benchmarks/prescribed_cycle.ini --cycle-field main_area_ratio --cycle-values 10,20,40
python tools/research_tp_reference.py verify results/research/reference-coverage/tp_v1_20261004
python tools/research_frozen_reference.py verify results/research/reference-coverage/frozen_v1
python tools/thermal_boundary.py verify results/research/thermal_boundary_v1
python tools/adiabatic_inlet.py verify results/validation/adiabatic_inlet_v1
python tools/adiabatic_study.py verify results/research/adiabatic_inlet_response_v1
python tools/feed_candidates.py check
python tools/feed_candidates.py check-header
python tools/liquid_anchor.py verify results/validation/liquid_anchor_v1
python tools/liquid_feed.py verify results/research/liquid_feed_reference_v1
python tools/liquid_table.py check
python tools/liquid_table.py verify results/validation/liquid_table_v1
python tools/liquid_combustion.py verify results/validation/liquid_combustion_v1
```

正式运行从manifest指向的新鲜已测构建开始。`build/release/rocketperf.exe`仅是便捷别名。新RunId不得覆盖旧记录；正式研究归档新增版本，保留成功、拒绝点、stdout/stderr和输入/构建/测试哈希。

## 接续方向与不可混用的边界

1. 当前优先完成两型工作方案、计算研究和证据复核；PPT、最终报告与发布任务后置，是否开工看worknow而不是旧日期计划。
   连续单相参考与C17查表已有；连续入口已接入HP/固定几何喷管。表格温压不是型号事实，泵/分流/循环仍须独立建模，化学质量、元素库存与能量边界不能跨模型混用。
2. 型号缺口仍见[RES-001](调研/专题/RES-001_型号版本与参数缺口.md)和参数台账。两型直接原文核验截至2026-10-03；本地整理不刷新在线事实。子型室压、面积比、O/F和工况比冲不能用同系列或制造背景拼接。
3. 循环热状态、密度、入口焓是给定条件。七点诊断已证实：入口焓变化只平移所需热量，密度变化经泵功/分流影响性能。约302 s是合成算例；约193.65 MW主室热排出不是冷却设计负荷，也不组成绝热真实循环。非零回流字段拒绝；液态温压/焓基准和煤油物性未知保留。
4. 越域不等于流动已分离。出口尺寸只是几何代价，不是喷管质量、侧载、冷却裕度或寿命。局部扰动不是有概率依据的置信区间。
   固定喉面积单喷管由通量求流量；原循环扫描固定流量后重新定尺寸。二者不混用。[显式焓HP](docs/adiabatic-inlet-validation.md)、[固定液态锚点HP](docs/liquid-anchor-validation.md)与连续液体HP各有Q=0边界，但没有重新闭合轴功/分流。气态相态/焓基准是调用方声明；固定液态记录的ID/温度精确验证也不证明相态稳定或压力修正，连续表只在声明域内使用。
5. 旧Grok摘要有比原文更强的型号断言，sanitizer返回也含错误；使用[审查记录](docs/review.md)和原文台账，不据摘要补数。Pyskyfire已固定7份源码并审查涡轮方程，没有整库移植。
6. 仅推进Windows构建/检查。历史WSL sanitizer结果保留，但不能证明新源码或Windows exe被插桩；远端CI未经本地实跑证明。

## 交给别人

按[接收与讲解说明](docs/receiving.md)固定Git提交、生成离线源码/运行包，再由接收者具名复跑成功与失败案例。旧包各自固定旧提交，不自动包含新增研究；只有干净提交和新鲜完整质量证据可生成新包。新v2包从任务快照按工作面接续顺序推荐，并核对对应关系，旧v1推荐不作为当前推进指令。软件复验不是独立科学审查。

固定液态锚点的代码、运行、真实失败与Windows检查见[计算快照](taskshot/2026-10-05_032-liquid-anchor.md)，干净源码复验见[接收记录](taskshot/2026-10-05_033-liquid-anchor-receipt.md)，包内接续任务修正见[修正记录](taskshot/2026-10-05_034-handoff-routing.md)。固定几何入口响应见[前序计算](taskshot/2026-10-05_029-inlet-response.md)和[固定提交接收](taskshot/2026-10-05_030-inlet-response-receipt.md)；入口候选见[研究快照](taskshot/2026-10-05_031-feed-properties.md)。原始来源、旧快照、参考输出和旧构建未删除或改写。每个实质批次落地本地提交，不自动推送。

ANA-010 的连续液体入口 HP、固定面积喷管、C/CEA 归档与当前质量/静态分析证据见[本轮快照](taskshot/2026-10-05_038-liquid-combustion.md)和[核验说明](docs/liquid-combustion-validation.md)。接手时不要把连续表温压当成两型真实入口；不要把软件对照当成实验；先以任务板和最新质量报告核对提交身份，再领取后续泵后边界、煤油或循环任务。
