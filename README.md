# 火箭发动机原理 · Rocketperf

研究朱雀三号与长征十号乙的动力系统，用C程序完成性能分析与改进研究。当前计算能力是**经过验证的理想气体教学基线**；真实参数、热化学与循环模型仍需研究。

[打开架构三视图](docs/architecture/index.html) · [当前工作](worknow.md) · [任务板](docs/tasks.md) · [治理规范](docs/governance.md)

技术路线已确定：[C17核心、零维/准一维/稳态模型、CLI与离线报告](docs/technology-stack.md)。该决定明确工具职责，不代表高级模型已实现。

![业务流程](docs/architecture/business.svg)

## 开始工作

需要Python 3.10+和GCC；PowerShell是可选兼容入口。根目录执行：

```powershell
python tools/project.py doctor
python tools/quality.py
python tools/pipeline.py run --case cases/benchmarks/air_mach2_vacuum.ini
```

运行工具核对新鲜的构建/测试证据，保存输入、实际二进制、报告和哈希到 `results/local/<RunId>/`。失败也保留记录。同名RunId不能覆盖。

## 按职责找入口

| 工作 | 入口 |
|---|---|
| 了解作业目标与完整研究方案 | [原始要求](作业要求/大作业1_要求存档.md)、[完整规划](docs/project-plan.md)、[研究结构](docs/research-structure.md) |
| 领取、交接、验收任务 | [worknow](worknow.md)、[handoff](handoff.md)、[治理命令](docs/governance.md) |
| 理解业务与模块边界 | [架构三视图及模块契约](docs/architecture/README.md)、[核心设计](docs/engineering.md) |
| 改C代码或算例格式 | [贡献指南](CONTRIBUTING.md)、[输入契约](docs/case-format.md)、[解析基准](docs/benchmarks.md) |
| 查文献与参数证据 | [调研索引](调研/README.md)、[证据台账](调研/证据与参数台账.md) |
| 写研究专题和结论 | [写作约定](docs/research-writing.md)、[研究议题](docs/research-agenda.md) |
| 管目录、构建和Git | [目录地图](docs/project-map.md)、[环境说明](docs/environment.md)、[治理规范](docs/governance.md) |

任务事实只维护在 `project/tasks.json`，worknow和任务板自动生成。模块与源码清单只维护在 `project/modules.json`，架构和两条构建路径共同使用。原始资料保留原路径和字节。

课程节点：2026-10-16，周五第3—5节；展示≤10分钟、提问≤5分钟。最终交源码、发布版、报告和PPT。当前工程通过不等于课程研究已经完成。

待补工作和本次发现见[审查记录](docs/review.md)。MinGW运行库问题及WSL sanitizer命令见[环境说明](docs/environment.md)。分支、HEAD和工作树状态看doctor；未添加远端或推送。
