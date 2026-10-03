# 项目交接

本文件讲接手方法和遗留风险；实时状态看[worknow](worknow.md)，分支与提交看doctor。

## 已有基础

当前C17核心仍是定比热理想气体教学基线。工程治理已转为结构化登记：任务流转、生成视图、模块依赖、不可变构建、测试/运行失败记录和Git提交检查。使用[架构浏览页](docs/architecture/index.html)理解业务及模块边界。

最短恢复：

```powershell
python tools/project.py doctor
python tools/project.py check
python tools/project.py show DATA-002
```

需要验收时运行 `python tools/quality.py`，按[治理规范](docs/governance.md)提交REVIEW再DONE。不要直接改Markdown状态，也不要把过期PASS拿来验收新输入。

## 下一步的研究入口

现有专题和空气算例只是阶段产物，尚不足以完成课程研究。原任务中的DONE不表示真实型号数据、热化学或循环已实现。待补项目、原因和验收要求见[审查记录](docs/review.md)；领取顺序看 `worknow.md`。最终报告的前置任务已补上，不能从教学算例直接跳到结题。

S1 的实现入口是 `rocketperf study area-ratio-ambient CASE.ini`，契约见[模型实现说明](docs/model-implementation.md)，验证见[分层验证](docs/model-validation.md)，研究结果见[两型分析与改进计算](docs/study-results.md)。扫描输出中的 `out_of_domain` 必须保留为越域诊断，不能被绘图或报告静默转成零值；真实型号缺失字段继续留在参数缺口清单。

型号/参数缺口见[RES-001](调研/专题/RES-001_型号版本与参数缺口.md)和`data/parameters/baseline.json`。遥二后缀、长十乙二级型号/台数/循环，以及四类对象的室压、面积比、O/F和比冲工况仍缺直接证据。DATA-002需要逐字段复查原文，不用同系列资料或拟合值填成真实参数。

技术路线见[技术选型](docs/technology-stack.md)：NASA9、受限气相HP平衡、温变冻结喷管和稳态循环；这些扩展尚未实现。MOD-001先做NASA9物性，REF-001运行固定版本CEA，MOD-002再做平衡与喷管。Python承担工程、独立校核和绘图；Pyskyfire源码固定与部件审查尚未完成，不能称为已移植。

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
