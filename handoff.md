# 项目交接

本文件讲接手方法和遗留风险；实时状态看[worknow](worknow.md)，分支与提交看doctor。

## 已有基础

当前C17核心包含定比热教学喷管、十物种NASA9物性、九物种气态CH4/O2的TP/HP平衡、冻结混合物、燃烧室冻结温变喷管和给定热状态的外排循环边界。工程治理采用结构化登记：任务流转、生成视图、模块依赖、不可变构建、测试/运行失败记录和Git提交检查。使用[架构浏览页](docs/architecture/index.html)理解业务及模块边界。

最短恢复：

```powershell
python tools/project.py doctor
python tools/project.py check
Get-Content worknow.md
```

需要验收时运行 `python tools/quality.py`，按[治理规范](docs/governance.md)提交REVIEW再DONE。不要直接改Markdown状态，也不要把过期PASS拿来验收新输入。

## 下一步的研究入口

现有专题和空气算例只是阶段产物，尚不足以完成课程研究。原任务中的DONE不表示真实型号数据、热化学或循环已实现。待补项目、原因和验收要求见[审查记录](docs/review.md)；领取顺序看 `worknow.md`。最终报告的前置任务已补上，不能从教学算例直接跳到结题。

S1 的实现入口是 `rocketperf study area-ratio-ambient CASE.ini`，契约见[模型实现说明](docs/model-implementation.md)，验证见[分层验证](docs/model-validation.md)，研究结果见[两型分析与改进计算](docs/study-results.md)。扫描输出中的 `out_of_domain` 必须保留为越域诊断，不能被绘图或报告静默转成零值；真实型号缺失字段继续留在参数缺口清单。

型号/参数缺口见[RES-001](调研/专题/RES-001_型号版本与参数缺口.md)和`data/parameters/baseline.json`。遥二后缀、长十乙二级型号/台数/循环，以及四类对象的室压、面积比、O/F和比冲工况仍缺直接证据。DATA-002已有逐字段复核、检查工具与假设记录；10月3日新原文复查见专题，不用同系列或制造背景参数填成飞行性能。

技术路线见[技术选型](docs/technology-stack.md)。NASA9见[物性验证](docs/thermo-validation.md)；TP/HP和温变冻结喷管见[模型与验证](docs/thermo-nozzle-validation.md)。CEA v3.3.4已成功构建并复跑固定参考，C核心现在可作同条件自动对照。Python承担工程、校核和绘图；Pyskyfire已固定7份源码/许可证并核验涡轮方程，范围见[部件调研](调研/专题/MOD-003_循环边界与部件参考.md)，没有移植上游物性或求解网络。

扫描归档使用 `python tools/pipeline.py run --study area-ratio-ambient --case cases/research/s1_area_ratio_ambient.ini`，不要用不带`--study`的单点运行代替扫描。运行工具保存实际网格、输入、二进制、测试和结果；计算失败不能伪装成正常越域点。

## 要保留的风险认识

- 旧01_grok/02_grok摘要中的具体子型/数量/循环表述比原文证据更强；以台账和原文核验为准。
- A/B构型、海平面/真空、主室/整机及单位边界不能混用。已有约1%口径差异保留，不擅自抹平。
- CoolProp两个旧失败入口已有替代；L06出版商全文仍存在获取限制，月份变化不代表全文已经读到。
- Windows CMake已补测；Ubuntu WSL下GCC13.3的ASan/UBSan也已实际运行，见[环境说明](docs/environment.md)。它检查Linux程序，不是Windows exe。远端CI仍未执行。
- 运行从manifest指向的具体已测构建开始；稳定exe路径只是兼容别名。原始v1运行记录保留，新的运行manifest为v2。
- 原始资料和历史快照保留。Grok本次sanitizer返回包含错误，原文核对记录在[审查记录](docs/review.md)；不要引用检索摘要中的虚构源码。
- 没有整项目对外发布许可证；已有参考仓库LICENSE不等于代码已采用它们。

选型历史：[TECH-001](taskshot/2026-10-01_005_technology-selection.md)；工程历史：[GOV-001](taskshot/2026-10-01_004_governance-upgrade.md)。本次修订见[运行库与补审记录](taskshot/2026-10-02_012-runtime-and-review.md)。

## 2026-10-03 接续注意

新数据库、134个Cantera软件对照状态和形成焓测试已经落地。不能沿用旧CLI测试报告：此前装饰器使测试被跳过，现已修正并要求流水线零跳过。当前Windows Release实际执行1175项物性检查、15组CLI，CMake四项CTest也已重跑。构建中出现的超时和CEA纯Fortran配置链接失败均保留，不计作通过；开启官方C绑定后成功构建，未修改上游算法。

新来源与研究影响见[10月3日核验](调研/专题/MOD-001_数据与参考核验.md)。不再反复搜索同一缺失参数。原输出空列表杂字节/反应物能量标签/冻结室热容的问题见复现说明；未公开的真实型号输入独立保留。

## TP/HP与冻结喷管接续

`rocketperf combustion hp 10000000 3.4 298.15 298.15`计算气态方法燃烧室；`combustion frozen`再给面积比和环境压力。该模型不是沿程平衡喷管，不处理液态入口、凝聚相、电离或结焦。TP输出焓残差是维持指定温度所需的能量差，不要求为零；HP则强制验收焓残差。

`python tools/combustion_reference.py`从新鲜已测构建复跑TP、HP、A10和A40冻结喷管。原始CEA参考保持不变，新C输出单独存档。九物种元素矩阵、六条反应驻点、混合物积分关系、元素/焓/连续/能量/熵/声速与失败保持输出都有测试。整机外排支路与轴功率见下节；改进代价/敏感性仍待后续研究，不由本阶段自动证明。

本次实际产物与失败修正见[执行快照](taskshot/2026-10-03_018-combustion-frozen-nozzle.md)。阶段结束后建立本地提交并核对clean，不以长期脏工作树作默认交接。下一任务以worknow的可领取契约为准；不把本阶段测试通过写成真实型号研究完成。

## 给定热状态外排循环接续

`rocketperf cycle prescribed cases/benchmarks/prescribed_cycle.ini`计算总消耗对应的泵功、涡轮分流、主/支推力和所需热交换。正式记录用`python tools/pipeline.py run --model prescribed-cycle --case cases/benchmarks/prescribed_cycle.ini`；与L0共用不可变构建/测试/运行哈希，成功前再重算86条计账方程。固定产物在`results/validation/prescribed_cycle_v1_20261004/`。

`return_fraction`和`return_pressure_drop_pa`必须为零；任何非零值失败，不是压力可达便能宣称补燃闭合。入口焓必须与NASA9形成焓同基准；密度、入口焓和温度都是给定条件，不是液态物性解。算例约302 s不属于目标型号；主室约193.65 MW热排出说明它不是绝热真实发动机循环。

Grok两次502未形成有效证据；原文HTTP固定核验另存，不把失败检索说成成功。完整公式、失败边界与验证见[循环说明](docs/cycle-validation.md)，本轮产物和失败记录见[快照](taskshot/2026-10-04_019-prescribed-cycle.md)。下一任务按worknow接续ANA-002的改进代价与敏感性，不跳到PPT/报告。
