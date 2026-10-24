# 大作业二：火箭发动机热力计算

本阶段围绕朱雀三号与长征十号乙发动机，研究化学平衡和推力室理想热力性能。先建立能解释、能复算、知道何时失效的C计算基线，再用证据筛选改进方向。真实型号缺失参数不得用假数填满。

## 从这里接手

1. 读[当前工作面](worknow.md)、[规则](rules.md)、[交接](handoff.md)。Agent另读[协作入口](AGENTS.md)。
2. 核对[教师要求与追踪矩阵](docs/requirements.md)，再读[项目地图](docs/project-map.md)找到需要的文件。
3. 在仓库根运行 `python tools/project.py doctor` 和 `python tools/project.py show TASK-ID`，按[任务操作说明](docs/governance.md)领取工作。
4. 研究从[基线继承审查](docs/baseline-audit.md)、[质量标准](docs/quality-standard.md)、[研究规划](docs/research-plan.md)进入。

这里不另建任务数据库。根 `project/tasks.json` 是唯一任务事实，本站[任务板](docs/tasks.md)只显示产物位于Work2的任务。所有命令默认在 `E:/Work/火发原理` 运行。

## 阅读导航

| 目的 | 入口 |
|---|---|
| 明确必须交什么 | [要求原图](作业要求.png)、[要求解析](docs/requirements.md) |
| 判断什么算高质量 | [质量标准](docs/quality-standard.md)、[实验模板](templates/experiment.md) |
| 理解业务架构和计算边界 | [业务架构](docs/business-architecture.md)、[架构图](docs/business-architecture.svg)；当前C模块另见[共享工程架构](../docs/architecture/README.md) |
| 了解先做什么、怎样收敛 | [研究规划](docs/research-plan.md)、[知识地图](docs/knowledge-map.md) |
| 查依据与未解决问题 | [来源台账](research/evidence.md)、[审查与不确定性](docs/review.md) |
| 阅读首轮调查与已采数据 | [调研入口](research/README.md)、[调查协议](research/survey-protocol.md)、[数据说明](research/data/README.md) |
| 理解组织决定与提示词取舍 | [决策记录](docs/decisions.md)、[启动词审阅](docs/prompt-review.md) |
| 找作业一正式成果与未完成责任 | [作业一就地归档](archive/work1/README.md) |
| 新增资料、结果、交付与执行快照 | [调研规范](research/README.md)、[结果规则](results/README.md)、[交付规则](deliverables/README.md)、[执行记录](taskshot/README.md) |

## 已核实的起点

2026-10-23启动盘点有9份原件，合计21,284,631字节；路径与SHA256见[原件清单](project/sources-20261023.json)。原称“PPT”的位置实际为课程PDF及NASA文档/数据目录，未发现同名 `.ppt`。原始启动词完整保留于[提示词](提示词/start0.md)。

教师允许化学平衡常数法或最小Gibbs自由能法；要求C语言、两型研究衔接、报告和四项电子交付。展示为10分钟、提问5分钟。“12月5日（周五）”与2026日历不符，需核对通知；不沿用作业一展示时长。

2026-10-24已开展五条主线首轮调研和原文采集，形成[方法](research/method-review.md)、[C引擎](research/c-engine-review.md)、[AI](research/ai-review.md)、[参数](research/parameter-review.md)和[基准契约](research/benchmark-contract.md)。新数值基准、AI收益和创新性仍待实验验证。Grok初始403后修正地址拼接，后续两主题返回结构化搜索轨迹，另一个请求仍无轨迹；逐次状态保留，原文另行核验，不把接口可返回当结论已验证。
