# 项目交接

接手先读[当前工作面](worknow.md)，运行`python tools/project.py doctor`。任务状态由登记生成；分支、提交和工作树以Git实况为准，不在这里重复维护测试数量。

## 现在有什么

- C17：定比热教学喷管、十物种NASA9、九种中性C/H/O气体TP/HP（温度或显式同基准气态焓入口）、冻结/固定面积喷管、给定热状态外排循环及单输入扫描。显式焓只闭合气相燃烧室和单喷管，不改循环。
- 固定参考：NASA9/Cantera软件对照、四个CEA受限气相方法工况、合成循环实际六状态CEA TP、五状态主室冻结喷管与11个固定面积C点、泵/涡轮解析极限。没有完整发动机独立实验或整机循环同条件外部参考。
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
```

正式运行从manifest指向的新鲜已测构建开始。`build/release/rocketperf.exe`仅是便捷别名。新RunId不得覆盖旧记录；正式研究归档新增版本，保留成功、拒绝点、stdout/stderr和输入/构建/测试哈希。

## 接续方向与不可混用的边界

1. 当前优先完成两型工作方案、计算研究和证据复核；PPT、最终报告与发布任务后置，是否开工看worknow而不是旧日期计划。
2. 型号缺口仍见[RES-001](调研/专题/RES-001_型号版本与参数缺口.md)和参数台账。两型直接原文核验截至2026-10-03；本地整理不刷新在线事实。子型室压、面积比、O/F和工况比冲不能用同系列或制造背景拼接。
3. 循环热状态、密度、入口焓是给定条件。七点诊断已证实：入口焓变化只平移所需热量，密度变化经泵功/分流影响性能。约302 s是合成算例；约193.65 MW主室热排出不是冷却设计负荷，也不组成绝热真实循环。非零回流字段拒绝；液态温压/焓基准和煤油物性未知保留。
4. 越域不等于流动已分离。出口尺寸只是几何代价，不是喷管质量、侧载、冷却裕度或寿命。局部扰动不是有概率依据的置信区间。
   固定喉面积单喷管由通量求流量；原循环扫描固定流量后重新定尺寸。二者不混用。[显式焓HP](docs/adiabatic-inlet-validation.md)已经实现气态Q=0边界，但没有重新闭合轴功/分流/液态入口。相态/焓基准是调用方声明；未知焓零点不能靠枚举变正确。
5. 旧Grok摘要有比原文更强的型号断言，sanitizer返回也含错误；使用[审查记录](docs/review.md)和原文台账，不据摘要补数。Pyskyfire已固定7份源码并审查涡轮方程，没有整库移植。
6. 仅推进Windows构建/检查。历史WSL sanitizer结果保留，但不能证明新源码或Windows exe被插桩；远端CI未经本地实跑证明。

## 交给别人

按[接收与讲解说明](docs/receiving.md)固定Git提交、生成离线源码/运行包，再由接收者具名复跑成功与失败案例。旧`build/handoff-20261004`和`build/handoff-b2c66e2`各自固定旧提交，不自动包含新增研究；只有干净提交和新鲜完整质量证据可生成新包。软件复验不是独立科学审查。

显式入口焓、Windows验收与架构更新见[本轮快照](taskshot/2026-10-05_028-adiabatic-inlet.md)；前序入口边界见[诊断快照](taskshot/2026-10-04_026-thermal-boundary-and-assignment.md)，源码复验方法见[接收记录](taskshot/2026-10-04_025-fixed-nozzle-receipt.md)。原始来源、旧快照、参考输出和旧构建未删除或改写。每个实质批次落地本地提交，不自动推送。
