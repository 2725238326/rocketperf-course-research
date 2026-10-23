# 项目地图与文档职责

Work2是活动研究入口；Git仓库根仍在上一级。作业一的[就地归档](../archive/work1/README.md)隔离旧文档导航，原位置可追溯。

```text
Work2/
├─ README.md / AGENTS.md         人与agent入口
├─ worknow.md                   自动生成的作业二工作面
├─ rules.md / handoff.md         稳定规则与简明接续
├─ 作业要求.png / 参考内容.png    原图，保留原址
├─ 提示词/start0.md              原始意图档案，不当实时状态表
├─ 火箭发动机原理-第五章…/        两份课程PDF、两份NASA手册和两份inp原件
├─ docs/                        要求、标准、规划、审查、知识与决策
│  └─ tasks.md                  自动生成的本阶段任务板
├─ project/sources-YYYYMMDD.json 原件身份快照；没有第二套tasks.json
├─ archive/work1/               作业一归档导航及完整性交付快照
├─ research/                    来源台账、检索、原文和有问题意识的笔记
├─ results/                     选定的输入/结果/失败/清单版本
├─ deliverables/                最终课程材料与需求闭合清单
├─ templates/                   实验、来源及执行记录模板
└─ taskshot/                    追加的实质批次执行历史
```

## 每类信息只维护一处

| 信息 | 主维护位置 | 下游使用 |
|---|---|---|
| 任务状态、负责人、依赖与契约 | 根 `project/tasks.json`，工具变更 | 根与Work2的工作面/任务板自动生成 |
| 模块、C源码清单与依赖 | 根 `project/modules.json` | 共享构建、依赖检查和架构 |
| 规范文档归属、原件保护 | 根 `project/policy.json` | 链接、保护、秘密和暂存检查 |
| 老师要求与逐项追踪 | [requirements](requirements.md) | 报告/交付闭合清单；任务进度只引用生成板 |
| 执行规则及操作 | [rules](../rules.md)、[governance](governance.md) | agent接手，不复制状态 |
| 质量定义与研究路线 | [quality-standard](quality-standard.md)、[research-plan](research-plan.md) | 实验协议明确实例化 |
| 来源身份与支持的主张 | [evidence](../research/evidence.md) | 研究笔记/报告逐项引用 |
| 决定与未解决问题 | [decisions](decisions.md)、[review](review.md) | 说明原因和解除条件 |
| 运行结果与当时做过什么 | results版本、taskshot批次 | 绑定输入/版本/日志，不用叙述冒充结果 |

## 与根工程的关系

生产C源码继续位于根src/include，算例、测试、固定物性继续用根cases/tests/data。Work2目前建立研究和治理，不凭空复制第二套求解器。后续需要新模块时先登记契约、构建和测试，再选择位置；不能在未登记的Work2/src放绕过检查的生产代码。

根docs、taskshot、results的历史产物按其原日期理解，不批量搬迁。日常不必读完这些旧档，只按[继承审查](baseline-audit.md)和任务的链接读取。根README、AGENTS、handoff已增加阶段路由。

临时PDF抽取和渲染、构建与试跑统一放根 `build/work2/`；它可再生且不进Git。选定研究档案进入Work2/results，禁止覆盖已有RunId。不要以新增大量空目录表示模块已经存在。
