# 作业二 Agent 接手入口

本目录是当前活动阶段，根目录仍是共享Git仓库和C工程。继承根[AGENTS](../AGENTS.md)和[rules](../rules.md)，具体教师要求以本目录[原图](作业要求.png)为准。

## 最短路径

1. [worknow](worknow.md) → [rules](rules.md) → [handoff](handoff.md)。随后读[要求](docs/requirements.md)，按任务需要读[地图](docs/project-map.md)中的专题。
2. 从仓库根运行 `python tools/project.py doctor`；用 `show TASK-ID` 读取契约，领取再执行。
3. 状态只经根 `tools/project.py` 维护，WIP为1。不要建立 `Work2/project/tasks.json`，不要手改任何生成工作面或任务板。
4. 有实质成果后补本目录taskshot、handoff和来源/决策，运行根 `python tools/quality.py`，提交验收并审查暂存区，建立本地检查点。

## 不可遗忘的边界

- [作业一归档](archive/work1/README.md)是就地归档；不批量移动共享源码、旧文档、冻结交付或原始材料。其未验事项保留原负责人和历史，不自动冒充完成，也不自动重启旧计划。
- 九份原件受[哈希清单](project/sources-20261023.json)保护。原始启动词是意图档案；运行规则在本目录rules，取舍见[提示词审阅](docs/prompt-review.md)。
- 检索只走指定Grok脚本，先DryRun；凭据运行时读取，禁止打印、复制进仓库或用浏览器UI检索。原文可HTTP核验；接口失败时继续本地工作并记录范围。
- 核心计算C17。AI、RL、GPU、A100等是候选，需有具体问题、传统对照、验证指标和停止条件；不为使用技术而改变课题。
- 区分教师硬要求、用户愿景、研究建议、外部来源和实算结果。已核实/推断/假设/未知分开。无独立证据不称真实发动机精度、首创或SOTA。
- 常规授权内自主推进；不自行派生子agent。不明缩写如“jev”保留未知，不替用户扩写。显著额外算力开销、外部发布/推送/外发和不可逆操作另有边界。

当前可接续任务以生成工作面为准。不要把文档中某次日期的“下一步”覆盖任务依赖与验收契约。
