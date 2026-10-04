# 项目交接

接手先读[当前工作面](worknow.md)，运行`python tools/project.py doctor`。任务状态由登记生成；分支、提交和工作树以Git实况为准，不在这里重复维护测试数量。

## 现在有什么

- C17：定比热教学喷管、十物种NASA9、九种中性C/H/O气体TP/HP、燃烧室冻结温变喷管、给定热状态外排循环及其单输入扫描。
- 固定参考：NASA9/Cantera软件对照、四个CEA受限气相方法工况、泵/涡轮解析极限。没有完整发动机独立实验或整机循环同条件外部参考。
- 工程：模块依赖、严格输入、不可变构建、失败运行记录、统一验收和固定提交交接。成功结果还要通过关系复算，不能只凭JSON可解析或数值为正。

架构看[三视图](docs/architecture/README.md)。模型限制看[热化学/喷管](docs/thermo-nozzle-validation.md)与[循环](docs/cycle-validation.md)。研究结果看[改进与代价](docs/improvement-analysis.md)，保存文件从[研究归档](results/research/README.md)进入。

## 怎么复跑

```powershell
python tools/project.py check
python tools/quality.py
python tools/pipeline.py run --model prescribed-cycle --case cases/benchmarks/prescribed_cycle.ini
python tools/pipeline.py run --case cases/benchmarks/prescribed_cycle.ini --cycle-field main_area_ratio --cycle-values 10,20,40
```

正式运行从manifest指向的新鲜已测构建开始。`build/release/rocketperf.exe`仅是便捷别名。新RunId不得覆盖旧记录；正式研究归档新增版本，保留成功、拒绝点、stdout/stderr和输入/构建/测试哈希。

## 接续方向与不可混用的边界

1. 当前优先完成两型工作方案、计算研究和证据复核；PPT、最终报告与发布任务后置，是否开工看worknow而不是旧日期计划。
2. 型号缺口仍见[RES-001](调研/专题/RES-001_型号版本与参数缺口.md)和参数台账。两型直接原文核验截至2026-10-03；本地整理不刷新在线事实。子型室压、面积比、O/F和工况比冲不能用同系列或制造背景拼接。
3. 循环热状态、密度、入口焓是给定条件。约302 s是合成算例；约193.65 MW主室热排出说明它不是绝热真实发动机模型。非零回流字段拒绝，尚无混合化学闭合、液态物性或煤油模型。
4. 越域不等于流动已分离。出口尺寸只是几何代价，不是喷管质量、侧载、冷却裕度或寿命。局部扰动不是有概率依据的置信区间。
5. 旧Grok摘要有比原文更强的型号断言，sanitizer返回也含错误；使用[审查记录](docs/review.md)和原文台账，不据摘要补数。Pyskyfire已固定7份源码并审查涡轮方程，没有整库移植。
6. 仅推进Windows构建/检查。历史WSL sanitizer结果保留，但不能证明新源码或Windows exe被插桩；远端CI未经本地实跑证明。

## 交给别人

按[接收与讲解说明](docs/receiving.md)固定Git提交、生成离线源码/运行包，再由接收者具名复跑成功与失败案例。旧`build/handoff-20261004`对应旧提交，不自动包含本轮研究；只有干净提交和新鲜完整质量证据可生成新包。软件复验不是独立科学审查。

本轮修正与证据见[审阅快照](taskshot/2026-10-04_021-audit-and-research.md)；前阶段见[QA-001快照](taskshot/2026-10-04_020-quality-and-handoff.md)。原始来源、旧快照、参考输出和本地旧构建未删除或改写。每个实质批次落地本地提交，不自动推送。
