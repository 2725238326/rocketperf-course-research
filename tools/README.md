# 工程行为的实现位置

所有工具使用Python标准库，无第三方Python运行依赖；物理计算仍在C核心。

| 工具 | 职责 |
|---|---|
| project.py | 任务状态机、派生文档、模块/目录/证据/Git检查 |
| projectlib.py | 路径边界、原子写入、OS锁、指纹和Git只读调用 |
| pipeline.py | 不可变构建、测试报告、运行生命周期和输出协议校验 |
| quality.py | 统一质量入口及完整PASS/FAIL证据 |
| combustion_reference.py | 从新鲜已测C构建复跑TP/HP/冻结A10/A40，对照固定CEA，检查守恒并存档 |
| render_architecture.py | 有布局设计的SVG、Mermaid、离线HTML三视图 |
| migrate_governance.py | 一次性迁移旧手工任务板；已有任务登记时拒绝再次运行 |
| wsl_gcc.ps1 | 为既有Ubuntu WSL获取经SHA256核验的GCC依赖；显式-Install才安装，不修改网络配置 |

PowerShell脚本是兼容入口，不再重复实现另一份构建/执行逻辑。工具输出和文档不包含Grok凭据；调研HTTP脚本仍独立在`调研/scripts/`。
