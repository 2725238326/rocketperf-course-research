# 火箭发动机原理大作业

研究对象：朱雀三号与长征十号乙动力系统。作业包含文献调查、发动机性能计算、优缺点与改进方案研究，核心计算使用C语言。

**开始工作：读 [worknow](worknow.md) → [rules](rules.md) → [handoff](handoff.md)。** Agent入口为 [AGENTS.md](AGENTS.md)。

## 当前阶段

已有v0.1.0工程基底：纯C17理想喷管核心、严格算例输入、JSON输出、解析基准和构建/测试/运行追溯。它使用教学理想气体数据，尚不能预测两型真实发动机性能。型号证据、热化学和循环模块继续按任务推进。

## 构建、验证和运行

需要PowerShell 7、GCC及用于测试的Python 3（标准库即可）。从根目录执行：

```powershell
pwsh -NoProfile -File ./scripts/test.ps1 -Configuration Debug
pwsh -NoProfile -File ./scripts/test.ps1 -Configuration Release
pwsh -NoProfile -File ./scripts/run-case.ps1
```

构建产物在`build/`；运行会打印`results/local/<RunId>/result.json`路径，并保存输入/二进制快照及哈希。已有RunId拒绝覆盖。Windows中文路径已纳入测试。

若只想查看JSON：`./build/release/rocketperf.exe run ./cases/benchmarks/air_mach2_vacuum.ini`。

## 常用入口

| 需要做什么 | 入口 |
|---|---|
| 确认老师到底要求什么 | [作业要求存档](作业要求/大作业1_要求存档.md)、[要求与交付映射](docs/requirements-map.md) |
| 看完整思路、模块、排期与分工 | [项目完整规划](docs/project-plan.md) |
| 开发核心、理解模型范围和输入 | [工程设计](docs/engineering.md)、[算例契约](docs/case-format.md)、[解析基准](docs/benchmarks.md) |
| 领取下一项工作 | [任务板](docs/tasks.md)、[全面调研议题](docs/research-agenda.md) |
| 找文件和判断放在哪里 | [目录与文档职责](docs/project-map.md) |
| 理解哪些路线已决定 | [决策记录](docs/decisions.md) |
| 阅读已有调研结论 | [调研索引](调研/README.md)、[综合调研报告](调研/综合调研报告_2026-09-29.md) |
| 查参数来源/冲突 | [证据与参数台账](调研/证据与参数台账.md) |
| 查开源工具和技术文献 | [开源工具与文献评估](调研/开源工具与文献评估.md) |
| 运行检索与本地检查 | [环境与运行说明](docs/environment.md)、[验证要求](docs/verification.md) |
| 了解上次做了什么 | [handoff](handoff.md)、[历史快照](taskshot/README.md) |

展示时间：**2026-10-16，周五第3—5节**。交付源代码、程序发布版、展示PPT和研究报告；展示≤10分钟、提问≤5分钟。分组人数在照片与本地课件中有冲突，实际安排待老师/助教确认。

从项目根目录执行一次只读检查：

```powershell
pwsh -NoProfile -File ./scripts/check-project.ps1
```

现有原始材料保留原路径。本地Git已初始化为main分支，尚无提交或远端；CI配置已提供，但本轮未运行远端CI或CMake。实际验证路径为本机GCC的Debug/Release。
