# 目录与文档职责

## 当前目录

```text
火发原理/
├─ AGENTS.md                  agent自动接手入口
├─ README.md                  给人的项目导航
├─ worknow.md                 当前阶段、正在做什么、下一步
├─ rules.md                   执行和证据维护规则
├─ handoff.md                 下一位agent的接手说明
├─ docs/
│  ├─ requirements-map.md     原始要求与交付覆盖
│  ├─ project-plan.md         完整研究思路、模型、算例、排期与分工
│  ├─ tasks.md                全量任务状态、依赖与验收
│  ├─ research-agenda.md      全面调研的问题清单
│  ├─ decisions.md            已确定、建议中、待决定的路线
│  ├─ verification.md         证据/算法/模型/交付验证
│  ├─ environment.md          本机环境与可执行命令
│  ├─ project-map.md          本文件
│  └─ templates/              研究记录与移植评估模板
├─ taskshot/                  按日期和序号保留工作快照
├─ scripts/check-project.ps1  离线、只读项目检查
├─ scripts/build.ps1          GCC Debug/Release构建和源码哈希
├─ scripts/test.ps1           核心及CLI验证
├─ scripts/run-case.ps1       输入/二进制快照和运行追溯
├─ include/rocketperf/        公共值类型、状态与计算API
├─ src/                      core/nozzle/adapters/cli分层实现
├─ tests/                    C检查、Python黑盒测试和解析参考
├─ cases/benchmarks/         人为定义的理想空气教学算例
├─ data/                     真实参数集契约说明，数据尚待建立
├─ third_party/              外部代码与许可边界说明
├─ results/local/            本地运行记录（忽略版本控制）
├─ CMakeLists.txt            待在CMake环境验证的备用构建
├─ .github/workflows/ci.yml  待远端执行的Windows/Linux检查
├─ 作业要求/                  老师要求转录及两张原图
├─ 调研/
│  ├─ README.md               已有研究文档导航
│  ├─ 专题/                  新一轮深入研究产出
│  ├─ 原始来源/              网页/仓库文档/元数据快照及索引
│  ├─ 文献/                  原始PDF与提取文本
│  ├─ 检索记录/              Grok原始返回，含历史不完整结果
│  ├─ prompts/               检索问题
│  ├─ scripts/               当前支持的研究辅助脚本
│  ├─ 工具/                  历史脚本和问题，保留但不作新入口
│  └─ *sources*.json          来源URL清单，现有脚本依赖此位置
└─ 第2章推力室和发动机的主要参数20260911.pptx
```

原始资料未搬迁。保留路径可避免历史文档、脚本和用户书签失效。新目录通过有内容的README或模板建立，不添加没有意义的占位代码。

## 每类信息只设一个主要维护位置

| 信息 | 主位置 | 其他文档的做法 |
|---|---|---|
| 老师要求 | 作业要求/大作业1_要求存档.md | 引用，不另编“老师要求” |
| 当前工作状态 | worknow.md | README只介绍阶段，handoff链接当前状态 |
| 所有任务及依赖 | docs/tasks.md | worknow只突出当前/下一项 |
| 用户约束与执行规则 | rules.md | AGENTS保留关键约束和入口 |
| 已作决定及理由 | docs/decisions.md | 研究建议不直接改写为已批准决定 |
| 历史执行记录 | taskshot/ | 不把worknow写成流水账 |
| 来源与参数判断 | 调研/证据与参数台账.md及专题证据表 | 报告用来源ID，避免另造相同ID |
| 原始证据 | 调研/原始来源、文献、检索记录 | 摘要引用原文；快照保持可追溯 |

## 实现目录职责与落地状态

| 未来目录 | 创建时机 | 内容边界 |
|---|---|---|
| `src/`、`include/` | 已创建，ENG-001 | 自己维护的C核心与接口，热化学/循环扩展未完成 |
| `data/parameters/` | 参数集结构落地 | 事实/假设/未知分离；含来源与版本 |
| `cases/` | 已创建 | 教学基准；真实型号数据仍需DATA-001 |
| `tests/` | 已创建 | 独立解析参考、守恒、数值和CLI边界 |
| `third_party/` | 已创建边界说明 | 尚无移植代码/依赖，不等于已完成许可选型 |
| `build/` | 已有Debug/Release | 可再生成的编译产物、构建和测试报告，不等于最终提交包 |
| `results/` | 已创建并有本地算例运行 | 输入、二进制、构建指纹及成功/失败记录，不放手填“仿真结果” |
| `deliverables/` | 报告和发布阶段 | 待提交的四项成果与复现说明 |

## 命名与归档

- 任务ID：`ORG-001`、`RES-001`、`DES-001`、`IMP-001`等，固定后不换义。
- 专题：`RES-001_型号版本与参数缺口.md`等，文件头写日期、任务ID、证据截止和状态。
- 检索Topic：`20261001_res001_cz10b_stage2`，避免重复已有输出；日期按实际执行日。
- taskshot：`YYYY-MM-DD_NNN_短标题.md`，同日序号递增。
- 来源ID：旧V/O/L编号含义不变；新来源先查索引，使用唯一ID，重新抓取加日期/修订标识，不覆盖旧快照。
- 大HTML（当前Pyskyfire验证页约44MB）按需定点读取，不整份塞入上下文。
