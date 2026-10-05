# 项目交接

接手先读[当前工作面](worknow.md)，运行`python tools/project.py doctor`。任务状态由登记生成；分支、提交和工作树以Git实况为准，不在这里重复维护测试数量。

## 现在有什么

- C17：定比热教学喷管、十物种NASA9、九种中性C/H/O气体TP/HP（气态温度/显式焓或固定液态反应物锚点）、冻结/固定面积喷管、给定热状态外排循环及单输入扫描。入口扩展只闭合燃烧室和单喷管，不改循环。
- 固定参考：NASA9/Cantera软件对照、四个CEA受限气相方法工况、合成循环实际六状态CEA TP、五状态主室冻结喷管与11个固定面积C点、泵/涡轮解析极限。没有完整发动机独立实验或整机循环同条件外部参考。
- 新气态研究：12组入口温度/O-F条件的HP和固定喷管响应，每组新跑CEA；见[结果与SVG](docs/adiabatic-inlet-study.md)。它不是液态预热或两型实装设计。
- 入口候选：[RES-006](调研/专题/RES-006_液态与煤油入口.md)锁定三份CEA单温度反应物锚点、CoolProp 7.1.0 EOS身份和NIST surrogate原文/摩尔分数；[数据](data/parameters/feed_property_candidates.json)含11条事实/未知记录。仅CH₄(L)/O₂(L)两条固定记录已提取为C常量，见[21次C/6次CEA方法验证](docs/liquid-anchor-validation.md)；候选JSON、EOS、RP-1/surrogate不作生产运行时输入。
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
```

正式运行从manifest指向的新鲜已测构建开始。`build/release/rocketperf.exe`仅是便捷别名。新RunId不得覆盖旧记录；正式研究归档新增版本，保留成功、拒绝点、stdout/stderr和输入/构建/测试哈希。

## 接续方向与不可混用的边界

1. 当前优先完成两型工作方案、计算研究和证据复核；PPT、最终报告与发布任务后置，是否开工看worknow而不是旧日期计划。
   固定液态锚点方法之后接续RES-007：先生成可追溯的连续单相离线参考、核对摩尔化学焓和插值拒绝域，再决定生产C17表格接入；不把无来源的温压点登记成型号事实。
2. 型号缺口仍见[RES-001](调研/专题/RES-001_型号版本与参数缺口.md)和参数台账。两型直接原文核验截至2026-10-03；本地整理不刷新在线事实。子型室压、面积比、O/F和工况比冲不能用同系列或制造背景拼接。
3. 循环热状态、密度、入口焓是给定条件。七点诊断已证实：入口焓变化只平移所需热量，密度变化经泵功/分流影响性能。约302 s是合成算例；约193.65 MW主室热排出不是冷却设计负荷，也不组成绝热真实循环。非零回流字段拒绝；液态温压/焓基准和煤油物性未知保留。
4. 越域不等于流动已分离。出口尺寸只是几何代价，不是喷管质量、侧载、冷却裕度或寿命。局部扰动不是有概率依据的置信区间。
   固定喉面积单喷管由通量求流量；原循环扫描固定流量后重新定尺寸。二者不混用。[显式焓HP](docs/adiabatic-inlet-validation.md)与[固定液态锚点HP](docs/liquid-anchor-validation.md)已经实现各自Q=0边界，但没有重新闭合轴功/分流或连续液态入口。气态相态/焓基准是调用方声明；固定液态记录的ID/温度精确验证也不证明相态稳定或压力修正。
5. 旧Grok摘要有比原文更强的型号断言，sanitizer返回也含错误；使用[审查记录](docs/review.md)和原文台账，不据摘要补数。Pyskyfire已固定7份源码并审查涡轮方程，没有整库移植。
6. 仅推进Windows构建/检查。历史WSL sanitizer结果保留，但不能证明新源码或Windows exe被插桩；远端CI未经本地实跑证明。

## 交给别人

按[接收与讲解说明](docs/receiving.md)固定Git提交、生成离线源码/运行包，再由接收者具名复跑成功与失败案例。旧`build/handoff-20261004`和`build/handoff-b2c66e2`各自固定旧提交，不自动包含新增研究；只有干净提交和新鲜完整质量证据可生成新包。软件复验不是独立科学审查。

固定液态锚点的代码、运行、真实失败与Windows检查见[本轮快照](taskshot/2026-10-05_032-liquid-anchor.md)。固定几何入口响应见[计算快照](taskshot/2026-10-05_029-inlet-response.md)和[固定提交接收记录](taskshot/2026-10-05_030-inlet-response-receipt.md)；入口候选见[研究快照](taskshot/2026-10-05_031-feed-properties.md)。显式入口焓见[前序快照](taskshot/2026-10-05_028-adiabatic-inlet.md)。原始来源、旧快照、参考输出和旧构建未删除或改写。每个实质批次落地本地提交，不自动推送。
