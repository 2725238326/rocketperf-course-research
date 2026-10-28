# 与九CHO基线有关的前沿核读：2026-10-28

本轮围绕HP累计成本、稳健性和下一步实验查新，选定三项方法，不称穷尽、最新最优或本项目创新。来源主索引累积75条、67条可核字节；本批7条中6份可得，包含同论文元数据/全文，**不是6篇独立论文**。精确范围及短引文见[结构化记录](data/frontier-20261028-v1.json)。

指定Grok新Topic `_a`先DryRun后HTTP502，保存脱敏失败；新Topic `_b`先DryRun后有7条工具记录。MaxCalls=4仅为提示预算。摘要经独立HTTP原文核对，无浏览器UI检索或凭据复制。

## FastChem 4：新工作与现有本地能力分开

**已核实事实。** Kitzmann、Stock、Patzer，*FastChem 4: New chemical elements and improved convergence behaviour*，[arXiv:2605.18264v1](https://arxiv.org/html/2605.18264v1)，2026-05-18；W2-F01/F02。读摘要与§2.1–2.3，未复现作者算例。§2.1.2明确“not to implement the Newton method as the default solver”：标准迭代慢时才插入多维Newton，默认400次触发，图2实验用300次。作者也指出大部分区域原方法已表现良好。

§2.2把元素数密度改用对数和log-sum-exp；§2.3的Levenberg–Marquardt/扰动Hessian回退属于凝相系统。论文面向天体/大气给定p-T平衡，含扩展元素/离子/凝相和GPLv3声明；本批没有核完整tag/许可证依赖或运行移植。

**推断/候选。** 借鉴“简单方法优先，慢/病态时才启用昂贵校正”的准入。当前C已有对数/log-sum-exp，不能把再次采用称新贡献；论文不直接证明本项目HP、Windows部署或收益。

## Combustion Toolbox：相近的HP外层方法线索

**已核实事实。** Cuadra、Huete、Vera，*Combustion Toolbox: An open-source thermochemical code for gas- and condensed-phase problems involving chemical equilibrium*，[arXiv:2409.15086v1](https://arxiv.org/html/2409.15086v1)，2024-09-23；W2-F03/F04。arXiv元数据列CPC320(2026)110004和DOI[10.1016/j.cpc.2025.110004](https://doi.org/10.1016/j.cpc.2025.110004)。实际读固定v1及元数据，不称精读2026出版社最终版。

已读§2.1/2.4、§3.1/3.3及火箭模块概要：MATLAB/GPLv3；NASA9默认可含Burcat/ATcT相关数据，不等于本项目CEA固定系数。§3.3解耦能量/熵约束，用Newton及“implicit third-order Newton-Steffensen root-finding algorithm”，参数研究可以前点温度初始化。其默认相对停止准则不同，不能只按迭代数排名。

**推断/候选。** WREF/WEXP比较Illinois、现有热启动和保护Newton/Brent时，固定质量门槛并计全部TP成本；平衡路径dh/dT不以冻结cp替代。解耦HP/热启动已有先例，不能作为本项目首创，不因此承诺整库C重写。

## JCP 2025变量重构：借鉴评价，不能直接换体系

**已核实事实。** Jonval、Ben Gharbia、Cancès、Faney、Tran，*Parametrization and Cartesian representation techniques for robust resolution of chemical equilibria*，JCP522(2025)113596，DOI[10.1016/j.jcp.2024.113596](https://doi.org/10.1016/j.jcp.2024.113596)，[HAL v3](https://hal.science/hal-04225504v3)。W2-F05为元数据，F06出版社403，F07作者开放全文34页；读PDF2–3、17–18、23–25页，渲染核对3/25页，未通读全部证明。

§2.1明确“diluted solutions of aqueous species”。§5使用Julia/ForwardDiff，实验均1bar、298.15 K，包含H2O、海水、水-混凝土，比较参数化、Cartesian与log-trick并结合线搜索。§5.3采用1000组随机右端项和多种初始化；PDF25页表3/4区分成功率/迭代统计，不能转为高温九CHO HP实证。

**推断/候选。** 借鉴低浓度压力集、初值分组及失败分母；若观测到4×4系统病态，先审查缩放/条件性/全局化，再决定是否变量重构。不把298.15 K水溶液化学势直接用于气相模型。

## 对本轮和下一步的影响

| 分类 | 实际动作或候选 | 边界 |
|---|---|---|
| 本轮已做 | 累计成本、同数据独立实现、原文范围、拒绝/驱动失败记录 | [基线报告](baseline-validation-v1.md)有实算证据；论文倍率未搬为结果 |
| 下一步优先 | 热启动/延拓与保护导数外层；残差缩放/Jacobian/少数病态点 | 待WREF/WEXP冻结，无收益照实否决 |
| 学习候选 | ODML和2026跨域可微研究继续作为先例，预测需真实残差/回退/总成本 | 见[AI调查](ai-review.md)；本批未获得新的可靠高温九CHO学习加速实证，不据有限检索说领域不存在 |
| 未知 | 完整最新软件正式版本清单、2020 ODML全文补核和方法全域排名 | 本轮只聚焦三项，旧固定版本未冒充最新，后续专题补采 |

摘要纠错已留档：把N2/Ar插入九CHO列表；把FastChem给定p-T及JCP稀水溶液方法称可直接用于HP。新知识先进入候选/验证设计，同模型、同门槛小实验有证据后才入生产C。后续路线冻结前按实际截止补定向查新，记录真正读过的范围和失败。
