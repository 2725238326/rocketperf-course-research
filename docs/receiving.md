# 阶段交接与验收

本文件给下一位维护者和讲解者使用。它把“程序能复跑”“证据完整”和“模型结论成立”分开，不把机械 PASS 说成科学结论。

当前交接的是 A、B 两部分的方法与工程基础，不是最终报告、PPT或真实发动机参数闭合。完整课程交付仍按 REL-001 的前置任务推进。

## 接手分工

一人可以承担多项职责，但交接时要写清姓名，不能只写“小组负责”。建议指定一个维护接口人和一个研究接口人，修改需求先落到具体任务。

| 接手职责 | 接收时核对 | 后续负责 |
|---|---|---|
| 维护 | 提交、构建、测试、成功/失败运行 | C17源码、输入契约、回归测试 |
| 研究 | 型号版本、来源、假设和比较口径 | 数据补证、改进代价、敏感性与结论 |
| 讲解 | 固定演示输入、预期输出和限制 | 讲解顺序、演示与问答；不临时改数据 |
| 验收 | 软件接收记录及逐项语义说明 | 确认产物对应契约，保留未验收项 |

## 五分钟接手检查

在项目根目录执行：

```powershell
python tools/project.py doctor
python tools/project.py check
Get-Content handoff.md
Get-Content worknow.md
```

确认分支、HEAD、工作树和任务状态后，再看[架构三视图](architecture/README.md)。不要把 `worknow.md` 或 `docs/tasks.md` 当作手工编辑文件。

## Windows 复跑

有现成交接包时，在包目录执行：

运行 exe 不需要编译器；完整包校验需要 Python 3.10+ 和 Git，源码重建另需 GCC。先用 `python --version`、`git --version`、`gcc --version` 确认工具，不把交出方本机路径复制成接收方的配置。

```powershell
python tools/handoff.py verify --package .
./rocketperf.exe cycle prescribed cases/benchmarks/prescribed_cycle.ini
./rocketperf.exe run tests/fixtures/overexpanded.ini
```

第二条应成功；第三条应明确失败，退出码为 4，不应输出成功结果。读包内 `START-HERE.md`；完整源码在 `source.bundle`，用 `git clone source.bundle rocketperf-source` 离线接手，不依赖远端已推送。源码目录的文档链接、doctor和quality不应在精简运行包里执行。

在完整源码工作区执行：

```powershell
python tools/quality.py
python tools/pipeline.py run --model prescribed-cycle --case cases/benchmarks/prescribed_cycle.ini
python tools/cycle_validation.py --archive-id HANDOFF-NEW-ID
```

`HANDOFF-NEW-ID` 必须是未使用的新目录名。交接包中的 exe 只用于演示和核对哈希；代码修改不能只运行旧 exe，必须重新构建、测试和生成新的运行记录。

## 讲解顺序

1. 先说课程研究问题和资料缺口，不把公开构型资料补成发动机性能卡。
2. 再说明输入、控制体和模型 ID：NASA9、九物种气相 TP/HP、冻结喷管、给定热状态外排循环。
   新`hp-h`/`frozen-h`需说明相态与形成焓基准，用[保存版本](../results/validation/adiabatic_inlet_v1/manifest.json)演示，不把气态零热交换燃烧室说成液态/整机闭合。
   `hp-liquid`/`frozen-liquid`另有[固定液态锚点版本](liquid-anchor-validation.md)，只用指定温度化学焓与元素库存；PowerShell反应物ID需加引号。讲清“液态反应物记录”不等于液体EOS、泵入口或整机性能。
3. 演示一个成功算例和一个失败边界，展示 stdout、stderr、run-manifest 和残差。
4. 展示独立参考与数据来源的定位，说明它们是同条件方法核验，不是飞行性能验证。
   用[固定喷管入口响应](adiabatic-inlet-study.md)讲解为什么比冲升高时推力可以略降；从清单定位原C/CEA输出，不只展示曲线截图。
5. 最后说明下一任务、未完成项和不能外推的结论。

## 不能省略的边界

- `prescribed_thermal_cycle_v1` 不是绝热真实发动机循环；热交换是给定状态的倒算量。
- 合成算例约 302 s 不能写成朱雀三号或长征十号乙性能。
- 回流、液态物性、泵图谱、冷却、瞬态、凝聚相和真实型号缺失参数仍未闭合。
- 质量工具通过只表示结构、数值和追溯契约通过，不替代参数原文复核或独立科学审查。

## 交接完成条件

接手者应回传：`doctor` 输出、`project check` 输出、质量报告路径、运行 manifest 路径、一个成功结果和一个预期失败结果，并明确自己负责的是维护、研究还是讲解。需要改模型边界时先改任务契约和模块登记，再实现和验收；不要直接改生成视图或历史归档。

运行包接收者可以生成具名复验记录（文件放在包外）：

```powershell
python tools/handoff.py receive --package . --actor 张同学 --role maintenance --output ../张同学-接收记录.json
```

角色参数可为 `maintenance`、`research`、`presentation` 或 `acceptance`。记录包含版本、包清单哈希、姓名、职责和实际成功/失败复跑。它不自动确认论文来源或模型结论；研究负责人另写“确认内容、未确认内容、原因、下一动作”。

文件哈希用于发现传输损坏和版本混杂，不是签名或防伪认证。交出方应通过可信对接渠道提供包清单 SHA256；接收者不能只相信包内自带的哈希。测试包会标注 `test_fixture=true`，不能作为正式交付。

新v2包含任务登记快照：推荐任务优先采用工作面显式接续顺序，未就绪时如实保留状态；没有有效显式候选才按READY的优先级和ID选择。verify核对推荐与快照一致。旧v1包仍可读取，但没有这项一致性证明；维护接续以完整源码的worknow和doctor为准，不因包里列出报告任务就提前做PPT。

## 实际对接安排

约半小时即可完成第一轮：前5分钟确认版本和角色，中间10分钟由交出方讲解输入→部件→喷管→整机口径，随后10分钟由接手者自己运行，最后5分钟确认问题清单和下一任务。出现失败先保留完整错误、输入及版本，不仅截一张图；对方先按接收检查复现，再讨论修复。

讲解常见问答：“是不是有限元？”——目前是 C17 零维热化学、准一维冻结喷管和稳态部件记账，不是有限元；“能否给出两型真实性能？”——尚缺批次对应输入与循环闭合，不能；“约302 s说明什么？”——只是给定合成输入下的整机口径示例。
