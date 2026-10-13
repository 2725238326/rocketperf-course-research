# 文档导航

按你要做的事进入文档。任务状态只看[工作面](../worknow.md)和[生成任务板](tasks.md)；本页负责导航，不维护第二份进度表。

## 先了解当前项目

1. [根目录 README](../README.md)：项目目标和最短运行命令。
2. [当前工作面](../worknow.md)：正在做什么、下一步和当前边界。
3. [四级段研究](two-vehicle-study.md)：朱雀三号遥一、长十号乙首飞一二级的事实、可运行情景及未知量。
4. [循环模型现状](engine-cycle-validation.md)：开式/补燃模型、条件性算例、参考对照和限制。
5. [项目解读](project-guide.md)：研究、程序和验证的完整讲解。
6. [收尾总览](final-overview.md)：现有成果、演示入口、接收代码的边界和最终材料缺口；[代码包审阅](incoming-code-review.md)保留具体问题与复现。

## 按工作查找

| 要做什么 | 阅读入口 | 维护边界 |
|---|---|---|
| 查课程要求与交付 | [要求存档](../作业要求/大作业1_要求存档.md)、[要求映射](requirements-map.md) | 老师要求和工程选择分开；最终报告/PPT状态看任务板 |
| 查两型来源和参数 | [两型研究](two-vehicle-study.md)、[证据台账](../调研/证据与参数台账.md)、[机器数据](../data/README.md) | 参数映射不等于实机求解输入 |
| 写专题或核验来源 | [专题索引](../调研/专题/README.md)、[研究写作](research-writing.md)、[轻量模板](templates/research-note.md) | 搜索摘要是线索；结论须回到有定位的原文 |
| 改热化学或喷管 | [工程契约](engineering.md)、[热化学与喷管验证](thermo-nozzle-validation.md)、[液体入口HP](liquid-combustion-validation.md) | 九气相模型和固定入口各有自己的有效域 |
| 改循环或和组员实现合并 | [循环集成对照](cycle-integration.md)、[新模型验证](engine-cycle-validation.md)、[旧外排模型](cycle-validation.md) | 旧模型仍有效；新模型为原型，两个模型ID不能混称 |
| 修改算例/CLI | [理想算例格式](case-format.md)、[推进剂比较格式](propellant-case-format.md)、[代码风格](coding-style.md) | 严格schema；失败不保存为成功结果 |
| 检查研究结果 | [验证要求](verification.md)、[模型验证总览](model-validation.md)、[研究归档](../results/research/README.md) | 软件PASS不等于型号或实验验证 |
| 构建、验收、接手 | [治理规范](governance.md)、[交接说明](../handoff.md)、[接收验收](receiving.md)、[交付说明](delivery.md) | 实时提交和质量状态通过命令读取 |

## 文档职责

- `README.md`：短入口和常用命令。
- `worknow.md`、`docs/tasks.md`：由任务登记生成的当前状态和任务契约。
- `docs/engineering.md`、模块验证文档：模型、接口和失败边界。
- `docs/two-vehicle-study.md`、`调研/专题/`：研究解释与引用；参数主记录在台账/JSON。
- `results/validation/`、`results/research/`：不可覆盖的验证或研究档案；`build/`仅放临时试跑。
- `taskshot/`、带日期的补记：发生过的工作快照，不改写为新鲜状态。
- `project/policy.json`：规范文档登记。新增规范文档要登记职责，生成文档不能手改。

## 当前相关入口

新循环原型已有统一工程质量、静态分析和正式研究归档；它仍受明确假设、家族级证据和九气相适用域限制。是否还有未关闭的任务契约、任务状态和下一步只看[工作面](../worknow.md)，不从本索引推断。
