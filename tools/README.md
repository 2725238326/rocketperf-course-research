# 工程行为的实现位置

日常治理/构建/运行/报告复算使用Python标准库，生产物理求解在C。重新生成独立Cantera参考需要可选外部环境；科学绘图的Matplotlib同样不进入核心依赖。不要把这些可选路径说成全部标准库。

| 工具 | 职责 |
|---|---|
| project.py | 任务状态机、派生文档、模块/目录/证据/Git检查 |
| projectlib.py | 路径边界、原子写入、OS锁、指纹和Git只读调用 |
| pipeline.py | 不可变构建、测试报告、运行生命周期和输出协议校验 |
| quality.py | 统一质量入口及完整PASS/FAIL证据 |
| check_data.py | 字段级来源、数据角色、单位/范围及假设检查；四级段映射的身份、版本/级段、模型与产物关联 |
| thermo_data.py / cea_reference.py | 固定物性与CEA原始数据/参考完整性；Cantera仅参考生成路径 |
| gas_checks.py / cycle_validation.py | 对保存状态和计账关系独立复算；不作生产平衡/循环求解 |
| cycle_study.py | 校核C扫描的逐点状态、比较量和有限步响应，归档与复验研究版本 |
| research_tp_reference.py | 从保存合成循环取实际主室/发生器TP条件，运行固定CEA与C并保存六状态参考 |
| research_frozen_reference.py | 指定TP的CEA主室冻结对照、C固定喉面积研究归档与离线数值复验 |
| thermal_boundary.py | 编排七组C入口焓/密度诊断，固定输入、记录身份和跨工况解析关系；不求液态物性 |
| adiabatic_inlet.py | 编排显式同NASA9基准气相HP与固定面积验证，保存新旧入口/拒绝点/原参考和身份，离线复算关系 |
| adiabatic_study.py | 固定Pc/喉出口几何的气相入口焓/O-F研究，保存51次C/12次CEA运行，复验并生成响应SVG |
| feed_candidates.py | 固定CEA液态反应物、CoolProp身份和NIST surrogate候选；提取两条C固定锚点常量，不求液体物性或生产平衡 |
| liquid_anchor.py | 编排固定液态锚点HP/冻结喷管的21次C和6次新CEA运行，核对入口/元素/几何与拒绝点，保留失败并离线复验 |
| liquid_feed.py / liquid_eos.py | 固定HEOS离线生成、独立系数复核、摩尔化学焓对齐及插值/拒绝检查；复核不需CoolProp，重新生成需要固定Windows参考wheel |
| liquid_table.py | 从固定参考生成C表/原输出测试常量，检查纯C的实际CLI密度/焓与拒绝协议，归档并离线复验 |
| liquid_combustion.py | 连续液体入口HP/固定面积喷管的C与显式焓CEA运行、守恒/身份和预期拒绝核验；不求生产物理 |
| handoff.py | 固定提交、离线源码bundle、已测程序及具名软件接收 |
| delivery.py | 固定提交生成纯C源码/Windows ZIP，五个C测试重建、隔离运行与逐文件/ZIP核验；GitHub上传由gh显式执行 |
| kerosene_reference.py / kerosene_probe.c | 固定RP-1产物集合比较、C研究驱动和保存结果复核；不提供国产煤油CLI接口 |
| kerosene_validation.py | 固定RP-1公共C API/CLI的33次运行、21张CEA卡和812项参考/关系复核 |
| combustion_reference.py | 从新鲜已测C构建复跑TP/HP/冻结A10/A40，对照固定CEA，检查守恒并存档 |
| assignment_diagram.py / render_architecture.py | 作业对接SVG、工程三视图、Mermaid与离线HTML；生成后需视觉核验 |
| migrate_governance.py | 一次性迁移旧手工任务板；已有任务登记时拒绝再次运行 |
| wsl_gcc.ps1 | 历史Linux运行库准备工具；当前Windows任务不运行它 |

PowerShell脚本是兼容入口，不再重复实现另一份构建/执行逻辑。工具输出和文档不包含Grok凭据；调研HTTP脚本仍独立在`调研/scripts/`。
