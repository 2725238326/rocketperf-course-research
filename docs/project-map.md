# 目录与信息职责

目录按**研究资料、计算实现、工程治理、可再生产物**组织，原始资料保持旧路径。

```text
火发原理/
├─ README.md / AGENTS.md       人与agent入口
├─ worknow.md                 生成的当前工作面
├─ rules.md / handoff.md       稳定约束与接手叙述
├─ project/                   任务、模块、目录策略、验收证据
├─ docs/
│  ├─ architecture/           三视图SVG/Mermaid/离线HTML
│  ├─ governance.md           任务/文档/Git/目录操作规范
│  ├─ engineering.md          计算核心设计契约
│  ├─ coding-style.md         C代码撰写规范
│  ├─ two-vehicle-study.md    四级段事实、方法结果和可计算边界
│  ├─ tasks.md                生成的完整任务板
│  └─ 其他专题                研究计划、要求、基准、协议、决策
│     验证类：verification.md（四层验证要求）、model-validation.md、
│     thermo-validation.md（NASA9单物种）、reference-reproduction.md（CEA复现）
│     入口类：project-brief.md（作业要交什么）、requirements-map.md、project-guide.md
├─ src/ + include/            C核心、适配器、CLI与公共API
├─ tools/                     治理、构建测试、运行记录的唯一行为实现
├─ scripts/                   PowerShell兼容入口和语法检查
├─ tests/ + cases/            独立基准、负向测试、教学/研究算例
├─ data/                     参数/假设、四级段方法映射和固定物性数据
├─ third_party/              外部移植与许可约定
├─ taskshot/                 不可静默改写的工作历史
├─ 作业要求/ + 调研/          课程要求、原图、论文、证据与研究专题
├─ build/                    可再生构建、测试、临时工具（忽略）
└─ results/
   ├─ validation/            选定方法校验档案（Git，保留原字节）
   ├─ research/              有版本的计算研究档案（Git）
   └─ local/                 本地成功/失败试跑（忽略）
```

## 单一来源

| 信息 | 主维护位置 | 约束 |
|---|---|---|
| 任务事实 | project/tasks.json | 命令操作；事件、状态和负责人一致 |
| 当前状态 / 任务板 | worknow.md / docs/tasks.md | 从登记生成，不手改 |
| 模块和生产C源码 | project/modules.json | 两条构建、依赖检查和架构共用 |
| 规范文档与根目录职责 | project/policy.json | 新根目录要登记，不随意散落文件 |
| 研究结论 | 调研/专题及证据台账 | 证据截止、版本和假设明确 |
| 原始证据 | 原始来源/文献/检索记录/作业要求 | 保留字节；修订新增日期版本 |
| 运行与构建 | manifest指向的不可变构建、results/local | 不覆盖RunId；失败也记录 |
| 历史与决策 | taskshot / docs/decisions | 工作历史与方案决定分别维护 |

## 文档生命周期

入口负责导航；规范负责约束；操作说明负责命令；研究文档负责论证；历史快照负责“当时做了什么”；生成文件负责展示登记状态。不在多个文件重复维护任务表、Git实况和当前测试计数。

新研究专题使用任务ID命名，结项后链接回调研索引。新模块先定义契约和源码归属，补测试，再更新架构与构建登记。thermo已有受限气相方法与单相液体表/入口HP，cycle仍是给定热状态的prototype；图中保持真实范围，不通过目录暗示高级模型已完成。

## 产物与存储

生产源码、规范、参数来源和选定验证/研究证据进Git。build/results-local/锁/缓存忽略。计算研究在results/research保留版本与清单；deliverables留给最终课程交付。失败试跑不搬进源码目录，原始文件不重复复制到规范文档群。

`python tools/project.py inventory`只读展示体积、大文件及旧构建候选；不会自动清理。原课件/论文/网页不属于可随意删除的缓存，已有44MB交互网页属于历史档案。未来新增超25MB内容需要先说明存储方案。

实际规则和Git检查见[治理规范](governance.md)；[架构三视图](architecture/README.md)表达业务与功能，不以这份目录树代替架构。

阶段交接包放在 `build/handoff-*`，包含可运行程序、核验工具和离线源码bundle，不进Git、不替代最终课程交付。接收方法和人员职责见[交接验收](receiving.md)。
