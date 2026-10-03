# RES-002：开源核心代码及 C 移植评估

## 研究问题

哪些公开项目能帮助本作业建立 C17 核心，哪些只能作为外部校核或方法参考？本记录按固定来源快照和 2026-10-02 的限定检索整理，不把“有 C API”写成“核心由 C 实现”。

## 结论

1. **NASA CEA 是热化学和理论火箭性能的主要参考，但不是全 C 核心。** 官方仓库语言为 Fortran；README 的 `core-c` 预设表示“编译 Fortran 核心并提供 C 绑定”，C 侧是 ABI/调用层。它适合做独立校核、输入输出和数据组织参考；本项目若直接链接它，交付说明必须写成外部 Fortran 求解器依赖。
2. **Pyskyfire 最贴近推力室、冷却和发动机循环的课程问题，但核心为 Python。** README明确包含推力室热力学、冷却通道和循环，并有RL10A-3-3A验证报告；它适合阅读模块边界、残差和验证报告，不能作为本项目的 C 核心。
3. **RocketCycles 适合借鉴稳态系统边界和循环残差。** 其README明确拆分 `cycle_functions.py`、`fluid.py`、`cycle_classes.py` 和 sizing 求解，使用 CoolProp/PyFluids、NASA多项式和RocketCEA；它是 Python/GPL-3.0，且明确是稳态一维模型，不能直接翻译后声称复现真实发动机。
4. **Cantera/CoolProp 只能作物性或平衡对照。** 两者有 C/C++ 接口，但不会替代本项目的 C 喷管/循环边界；CoolProp也不是燃烧产物平衡软件。

## 项目评估矩阵

| 项目 | 固定证据 | 真实调用链/依赖 | 验证范围 | 本项目决定 |
|---|---|---|---|---|
| NASA CEA | `调研/原始来源/O01_cea_repo.txt`、`O01_cea_readme.txt`；Apache-2.0；仓库主语言Fortran | 输入卡/数据文件 → Fortran求解器 → `libcea`/`cea.h` C绑定；需要`thermo.lib`、`trans.lib`，构建用CMake和Fortran编译器 | 官方样例、热化学/火箭性能能力；本轮未把新版本完整构建称为已验证 | 主要理论/算例参考和独立校核；不链接进“全C核心” |
| Pyskyfire | `O07_pyskyfire_repo.txt`、`O07_pyskyfire_readme.txt`；MIT；Python | Python包 → 热化学/物性依赖 → 推力室、冷却、循环对象 → 报告；开发依赖含测试/文档/可视化 | RL10A-3-3A案例和仓库测试；不能迁移成目标型号验证 | 参考模块分层、输入输出和验证叙述；不直接移植整库 |
| RocketCycles | `O08_rocketcycles_repo.txt`、`O08_rocketcycles_readme.txt`；GPL-3.0；Python | `cycle_classes.py`组织架构，`cycle_functions.py`计算部件，`fluid.py`调状态，sizing调用外部优化/求根；依赖PyFluids/CoolProp、RocketCEA、NASA多项式 | 稳态一维循环和单元测试；README明确不含完整管损、传热、轴机械损失及瞬态 | 只按数学关系和控制体重新实现所需小模块，避免复制GPL代码 |
| Cantera | `O04_cantera_*`；BSD-3-Clause文本；C++核心、有C接口 | C++引擎经C API暴露；物种/反应机制和热力性质由数据文件驱动 | 通用化学平衡/动力学，不是本题目标型号的火箭验证 | 可作小规模平衡独立对照，默认不作为运行依赖 |
| CoolProp | `O05_coolprop_*`；MIT；C++核心/C API | C API调用共享库；纯流体/混合物状态由库和输入决定 | 流体热物性；不做燃烧平衡和喷管性能 | 仅在低温推进剂供给或冷却输入需要时对照 |

## 允许的移植边界

### 可以独立用 C 重写

- NASA RP-1311 中与本题直接相关的 NASA9 物性评价、定温定压受限气相平衡、定压绝热焓平衡、冻结组分准一维喷管方程。
- RocketCycles/Pyskyfire中可由方程和接口重新表达的质量守恒、能量/轴功率平衡、残差缩放和参数扫描框架。
- 课程需要的输入校验、二分/阻尼Newton/LU、结果JSON和失败语义。

### 不能包装成“全 C”

- C程序只调用 CEA 的 `libcea`，但求解仍由 Fortran完成。
- Python CLI调用 RocketCEA/Pyskyfire/RocketCycles，再把输出转成 JSON。
- 只移植外层类名，继续依赖原项目的物性库、优化器或数据库，却在报告中称“C实现”。

### 许可证与数据边界

- Apache/MIT/BSD/GPL 是项目代码许可，不自动覆盖外部 NASA9/热化学数据库。
- 若只依据论文公式独立实现，不等同于复制 GPL 源码；若复制或改写具体代码，必须保留来源并按实际分发方式履行许可证。
- 本轮没有找到“覆盖热化学、喷管、循环且核心纯 C”的现成项目；这只是本轮检索范围内的结论，不是对所有项目的不存在证明。

## 对项目架构的落实

1. `src/thermo/`、`src/nozzle/`、`src/cycle/` 只接受本项目定义的 C 接口和版本化数据，不把第三方对象直接穿透到业务层。
2. `tools/` 可运行外部参考软件和解析脚本，但所有对照输入、版本、数据库和输出哈希必须保存到 `调研/` 或 `results/`。
3. 首版先以自有 C 实现 `ideal_constant_gamma_v1` 回归，再逐层加入 NASA9/平衡/冻结喷管；每一步都需要独立参考或守恒测试。
4. 如果高级热化学模块未能在截止日前通过验证，交付保留可复现 C 基线和条件性扫描，不用外部软件输出填充缺失的 C 结果。

## 下一步

进入 `RES-003` 抽取课程公式和独立基准；随后由 `DATA-001` 建立事实集、假设集、校核集分离的参数文件，再进入 `DES-001` 冻结首版模型接口。

