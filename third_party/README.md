# 外部代码与许可

当前C算法按热力关系独立实现，没有复制或链接NASA CEA、RocketCycles、Pyskyfire、Cantera或CoolProp求解代码。NASA9固定系数、CEA反应物记录以及HEOS离线派生查表属于数据依赖，各自保留来源/许可；不能把“无求解库链接”说成“完全没有第三方内容”。运行依赖C运行库/数学库；Python用于工程、校核和归档。

ANA-008的`src/thermo/reactants_generated.h`同样是CEA v3.3.4固定数据提取，含两条指定温度反应物化学焓/分子量/元素式，不是CEA算法移植。来源SHA256与位置见[液态方法](../docs/liquid-anchor-validation.md)和RES-006；上游LICENSE/NOTICE仍保留并随源码交接，不以生成C常量免除数据许可追踪。

后续移植外部模块时，必须记录仓库/原文件、固定commit、许可证、保留声明、修改范围、底层依赖及验证案例。不同许可不能通过改写语言消除。

本项目尚未由用户选择对外发布许可证，因此未擅自添加MIT/Apache/GPL等整项目许可声明。现有上游LICENSE原文仍位于`调研/原始来源/`，不代表它们已成为代码依赖。

MOD-003只参考Pyskyfire固定commit的涡轮方程和测试职责，没有复制其CoolProp调用或网络求解器；源码/许可原文与逐文件哈希见[核验专题](../调研/专题/MOD-003_循环边界与部件参考.md)。保留上游MIT原文不改变整项目未选择对外许可证的状态。

ANA-004的[frozen_v1](../results/research/reference-coverage/frozen_v1/manifest.json)另保存CEA v3.3.4固定commit的`source/main.f90`和`source/rocket.f90`原字节，只用于核查指定TP与冻结位置；未修改、未编入本项目核心。上游Apache-2.0 [LICENSE](../调研/原始来源/20261003_cea_v3.3.4/LICENSE.txt)与[NOTICE](../调研/原始来源/20261003_cea_v3.3.4/NOTICE.txt)保持原文并随完整源码交接保留；来源提交和逐文件哈希见归档清单。

RES-007 的[连续液体参考](../results/research/liquid_feed_reference_v1/manifest.json)包含 CoolProp 7.1.0 HEOS 的导出流体JSON和计算数据；它是参考侧依赖。保留官方 [MIT LICENSE](../调研/原始来源/F04_coolprop_license_7_1_0.txt)和 [BibTeX](../调研/原始来源/F07_coolprop_bibliography_7_1_0.txt)，生成数据由 CEA 理想零点对齐、参考域与插值规则派生，修改范围见[契约](../docs/liquid-feed-contract.md)。Python 系数复核按 Helmholtz 数学关系实现，没有复制上游求解器代码；后续生成 C 数据仍须携带这些来源和许可。

ANA-009 的 `src/thermo/liquid_feed_generated.h`从上述固定参考提取407对密度/摩尔焓；`tests/reference/liquid_feed.h`另提取700内部软件参考及全部节点，用于核对C插值误差。只作数据提取与质量焓换算，没有移植HEOS求解器；MIT原文和CEA LICENSE/NOTICE继续随完整源码交接保留。
