# 工程行为的实现位置

日常治理/构建/运行/报告复算使用Python标准库，生产物理求解在C。重新生成独立Cantera参考需要可选外部环境；科学绘图的Matplotlib同样不进入核心依赖。不要把这些可选路径说成全部标准库。

| 工具 | 职责 |
|---|---|
| project.py | 任务状态机、派生文档、模块/目录/证据/Git检查 |
| projectlib.py | 路径边界、原子写入、OS锁、指纹和Git只读调用 |
| pipeline.py | 不可变构建、测试报告、运行生命周期和输出协议校验 |
| quality.py | 统一质量入口及完整PASS/FAIL证据 |
| check_data.py | 字段级来源、数据角色、单位/范围及假设检查 |
| thermo_data.py / cea_reference.py | 固定物性与CEA原始数据/参考完整性；Cantera仅参考生成路径 |
| gas_checks.py / cycle_validation.py | 对保存状态和计账关系独立复算；不作生产平衡/循环求解 |
| cycle_study.py | 校核C扫描的逐点状态、比较量和有限步响应，归档与复验研究版本 |
| research_tp_reference.py | 从保存合成循环取实际主室/发生器TP条件，运行固定CEA与C并保存六状态参考 |
| research_frozen_reference.py | 指定TP的CEA主室冻结对照、C固定喉面积研究归档与离线数值复验 |
| handoff.py | 固定提交、离线源码bundle、已测程序及具名软件接收 |
| combustion_reference.py | 从新鲜已测C构建复跑TP/HP/冻结A10/A40，对照固定CEA，检查守恒并存档 |
| render_architecture.py | 有布局设计的SVG、Mermaid、离线HTML三视图 |
| migrate_governance.py | 一次性迁移旧手工任务板；已有任务登记时拒绝再次运行 |
| wsl_gcc.ps1 | 历史Linux运行库准备工具；当前Windows任务不运行它 |

PowerShell脚本是兼容入口，不再重复实现另一份构建/执行逻辑。工具输出和文档不包含Grok凭据；调研HTTP脚本仍独立在`调研/scripts/`。
