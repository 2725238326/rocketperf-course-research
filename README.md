# 火箭发动机原理 · Rocketperf

研究朱雀三号与长征十号乙的动力系统，用C程序完成性能分析与改进研究。当前C核心包含定比热教学喷管、固定NASA9物性、九物种气态CH4/O2的TP/HP平衡、燃烧室冻结温变喷管和给定热状态的稳态外排循环边界。真实型号输入仍有缺口；方法基准和循环合成算例不能当作飞行发动机性能。

[打开架构三视图](docs/architecture/index.html) · [当前工作](worknow.md) · [任务板](docs/tasks.md) · [治理规范](docs/governance.md)

交给其他同学时先看[阶段交接与接收验收](docs/receiving.md)。干净提交和完整质量通过后，`python tools/handoff.py create --destination build/handoff-NEW-ID`生成本地运行包与离线源码bundle；不依赖远端已推送，不等同于最终课程发布。

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

## 实际运行燃烧与喷管

完整质量检查后，在Windows本地运行气态方法基准：

```powershell
./build/release/rocketperf.exe combustion hp 10000000 3.4 298.15 298.15
./build/release/rocketperf.exe combustion frozen 10000000 3.4 298.15 298.15 40 0
python tools/combustion_reference.py
```

第一条算燃烧室温度和组分；第二条继续算冻结喷管；第三条从已测具体构建复跑四个固定工况、与CEA自动比对并保留记录。`build/release`中的exe是便捷别名，追溯以manifest指向的实际构建为准。条件与验证见[热化学与喷管](docs/thermo-nozzle-validation.md)。

循环合成算例可直接运行并归档：

```powershell
python tools/pipeline.py run --model prescribed-cycle --case cases/benchmarks/prescribed_cycle.ini
```

该命令输出并保存泵功、涡轮轴功、外排支路、两路推力及热交换/残差。首版拒绝非零涡轮回流，不是完整补燃循环，见[循环边界与验证](docs/cycle-validation.md)。

实际研究入口：

```powershell
python tools/pipeline.py run --case cases/benchmarks/prescribed_cycle.ini --cycle-field main_area_ratio --cycle-values 10,20,40
```

C扫描产生完整状态、推力/比冲变化、出口面积/直径和有限步响应；Python检查、保存，不代替求解。结果与边界见[改进分析](docs/improvement-analysis.md)和[研究归档](results/research/README.md)。当前重点是这些计算与证据，PPT/最终报告暂不推进。

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

待补工作和本次发现见[审查记录](docs/review.md)。MinGW运行库问题及历史WSL验证见[环境说明](docs/environment.md)。分支、HEAD、远端配置和工作树状态看doctor；阶段完成建立本地提交，不自动推送。
