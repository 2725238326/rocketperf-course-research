# Handoff：下一位维护者

本文件讲接手方法和遗留风险；实时状态看[worknow](worknow.md)，分支与提交看doctor。

## 已有基础

当前C17核心仍是定比热理想气体教学基线。工程治理已转为结构化登记：任务流转、生成视图、模块依赖、不可变构建、测试/运行失败记录和Git提交检查。使用[架构浏览页](docs/architecture/index.html)理解业务及模块边界。

最短恢复：

```powershell
python tools/project.py doctor
python tools/project.py check
python tools/project.py show RES-001
```

需要验收时运行 `python tools/quality.py`，按[治理规范](docs/governance.md)提交REVIEW再DONE。不要直接改Markdown状态，也不要把过期PASS拿来验收新输入。

## 下一步的研究入口

默认继续RES-001型号/参数证据。RES-002源码移植评估和RES-003课程/文献基准也有契约。已有教学核心可复用，不要重建空工程；也不能把它当作已经完成的热化学、循环或真实型号求解器。

DOC-002正在整理研究结构和写作约定。它要求专题只回答实际问题，引用已有来源台账，区分事实/假设/模型结果，并用一项下一步动作收尾；不要把研究写成套话密集的章节模板。

技术路线已由用户授权确定，见[选型冻结](docs/technology-stack.md)：NASA9/受限气相HP平衡、温变冻结喷管、稳态循环，全部C实现；CEA主参考、Pyskyfire优先部件参考。RES-002应落实选定路线的源码/数据和验证，不再泛泛重选同一批框架。Python只承担工程、独立校核和绘图，Matplotlib已可导入但项目绘图模块未实现。

## 要保留的风险认识

- 旧01_grok/02_grok摘要中的具体子型/数量/循环表述比原文证据更强；以台账和原文核验为准。
- A/B构型、海平面/真空、主室/整机及单位边界不能混用。已有约1%口径差异保留，不擅自抹平。
- CoolProp两个旧失败入口已有替代；L06出版商全文仍存在获取限制，月份变化不代表全文已经读到。
- CMake本机路径已补测；远端CI、Linux sanitizer和其他编译器不能凭配置文件存在就说通过。
- 运行从manifest指向的具体已测构建开始；稳定exe路径只是兼容别名。原始v1运行记录保留，新的运行manifest为v2。
- 原始资料受Git保护，不通过重建来源索引来掩盖不明字节变化。新增资料使用日期/ID区分。
- 没有整项目对外发布许可证；已有参考仓库LICENSE不等于代码已采用它们。

最近选型记录：[TECH-001](taskshot/2026-10-01_005_technology-selection.md)；工程重构记录仍见[GOV-001](taskshot/2026-10-01_004_governance-upgrade.md)。下一次任务保留自己的输入、产物、失败与验收记录，不复制上一轮通过结论。
