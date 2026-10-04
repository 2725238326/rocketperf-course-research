# ANA-005：入口边界与作业对接

日期：2026-10-04。该快照记录本轮实际运行和设计产物，不把软件检查写成独立科学审查。

## 本轮产物

- `tools/thermal_boundary.py`：复用已测Release的C循环，生成七组单输入诊断，保存输入、结果、stdout/stderr、构建与测试身份；校验入口焓/密度的解析传播。
- `results/research/thermal_boundary_v1/`：基线、燃料/氧化剂入口焓各±100 kJ/kg、燃料/氧化剂密度各×0.9，共7份运行；每点132条状态检查。
- `docs/research-thermal-boundary.md`：逐字段来源分类、热量符号、数值结果、冷却边界、绝热气相后续契约。
- `tools/assignment_diagram.py`、`docs/architecture/assignment.svg`、`assignment.mmd`：作业三条研究要求与证据、C计算、改进研究、验证和四项交付的总览图。
- `tests/test_cycle.c`、`tests/test_cycle_reference.py`、`tests/test_governance.py`：入口传播回归、重新计算哈希后的错误归档反例、SVG链接与要求ID检查。

## 实际C结果

Release测试在Windows GCC14.2.0通过：core 207，adapters 29，thermo 1175，combustion 2544，cycle 353，CLI 27组；七次归档运行成功，`python tools/thermal_boundary.py verify results/research/thermal_boundary_v1`通过。

基线为两泵轴功1,137,201.607646 W、外排支路0.674224777 kg/s、发生器所需热输入2,081,320.441898 W、主室所需热交换−193,654,903.652555 W、总推力296,254.198769 N、整机等效比冲302.095209647 s。

入口h各±100 kJ/kg时泵功、流量、涡轮、喷管、推力和比冲不变；Q按分流质量解析平移。单侧密度×0.9时泵功、分流增加，推力分别为296,186.385286 N（燃料）和296,174.612256 N（氧化剂）。这只是给定热状态合成模型的输入响应。

## 边界判断

- −4.65 MJ/kg与0 J/kg接近298.15 K气态NASA9查询，不构成液态物性证据；422/1141 kg/m³是无来源合成密度。
- 主室约193.65 MW是维持给定温度的控制体所需排热，缺少几何、沿程换热、壁材和冷却剂模型，不能当真实冷却负荷。
- 当前图和文档区分老师要求、项目实现选择、已有方法、未覆盖范围；不画完成率，不把合成结果说成两型绝对性能。
- PPT、最终报告、真实液态/煤油入口、完整硬件循环、冷却/分离/寿命仍后置或未覆盖。

## 验收与提交

本轮先运行专题测试和项目检查，再重新生成架构图并用Sharp渲染PNG做视觉核对。项目检查与热边界归档验证通过，循环参考13组、治理20组通过。独立Windows CMake/Ninja Release实际构建，6/6 CTest通过，记录在`build/cmake-ana005/Testing/Temporary/LastTest.log`。

完整`python tools/quality.py`已在本轮文档/代码冻结后重新执行，6/6 PASS，质量指纹`3a88fa5cab73e3990f13079e39c9bfe59e59ef130697eb9cdd2894d3d7c3008c`。Debug/Release各4308项C检查（207+29+1175+2544+353）、CLI27组，参数8/物性5/CEA15/循环参考13组；治理20、runner25、交接6组，零跳过。

ANA-005已按三条契约提交并完成，验收证据为`project/evidence/ANA-005_73da88fabaf3.json`。ANA-006登记为接续的显式入口焓绝热气相方法，DOC-001增加该前置，避免核心研究未完就开PPT/报告。软件与关系复核不冒充另一个人的科学审查。目录只读盘点，未删除原始证据、旧运行或构建；本轮不新增在线检索。

审查暂存区并提交本地Git，不推送远端；提交后的独立检出与新固定提交交接包另记接收快照，不回写旧归档。
