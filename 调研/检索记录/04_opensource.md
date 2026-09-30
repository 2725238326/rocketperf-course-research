# 04_opensource

检索日期：2026-09-29；来源：Grok联网检索。此文件是检索返回内容，需结合正文来源审核。

先检索官方仓库与文档入口，再打开 README、LICENSE 与发行记录核对 C API 与液体火箭适配边界。

已定位官方入口。接下来打开 README、LICENSE、C 接口文档和液体火箭循环项目页面核对实现语言与维护日期。

继续打开 C 接口、LICENSE、发行记录和液体火箭循环项目文档，核对核心语言与维护日期。

**结论（截至2026-09-29）：** C语言火箭发动机**理论性能**课程作业可以做，最直接路径是官方 **NASA CEA v3** 的 **C绑定**（Fortran 2008核心 + C API，含 `cea_rocket_solver`）。C接口≠C核心。液体火箭**循环**（泵/涡轮/再生冷却闭环）没有成熟、可核验的C核心开源库；能找到的循环项目是Python。EcosimPro/ESPSS不是开源替代。pyCycle明确面向喷气发动机，不能当液体火箭循环开箱即用。

## 资料表

| 项目 | 仓库 | 许可证 | 核心语言 | C API | 能力/缺口 | 可核实维护 | 安装依赖 | 对本作业 |
|---|---|---|---|---|---|---|---|---|
| NASA CEA v3 | https://github.com/nasa/cea | Apache-2.0（LICENSE.txt正文） | Fortran 2008 | 有：C绑定Fortran API；`core-c`预设；文档标部分函数deprecated | 化学平衡、理论火箭性能、爆轰、激波；非泵/涡轮循环 | 文档3.3.4；CHANGELOG `[3.3.4] - 2026-08-28`；NESC TB 2026-08-21 | 源码：gfortran≥10或ifort 2021+、CMake≥3.19；Python包需3.11+ | **首选C调用库** |
| RocketCEA | https://github.com/sonofeft/RocketCEA | GPL-3.0 | Python + 修改后的遗留CEA2 Fortran（f2py） | 无官方C API | rocket模式Isp/C*/Tcham等；非nasa/cea v3；非全循环 | PyPI 1.2.3，Released Jan 19, 2026 | numpy/matplotlib；源码需gfortran；Win可预编译wheel | 不适配纯C作业；copyleft |
| RocketIsp | https://github.com/sonofeft/RocketIsp | GPL-3.0 | Python | 无 | 简化JANNAF交付Isp；依赖RocketCEA+RocketProps | 文档页标注2026-07-19 | Python；间接依赖RocketCEA | 只作交付Isp参考，非C库 |
| Cantera | https://github.com/Cantera/cantera | BSD-3-Clause（License.txt） | C++ | 有，但官方写experimental；3.2 generated CLib；legacy将于3.3删除 | 平衡/动力学/输运/反应器；无官方火箭性能模块 | 稳定版3.2.0（发布页2025-11-18）；README写dev 4.0.0a2 | pip/conda或SCons编译 | 可做平衡对照；C API不稳定 |
| CoolProp | https://github.com/CoolProp/CoolProp | MIT | C++ | 共享库C API：`CoolPropLib.h` | 流体热物性（类REFPROP）；不做CEA式火箭性能 | 文档8.0.0（2026-06-27）；组织页更新2026-09-28 | CMake；Python可用pip | 只适合物性，不替代CEA |
| OpenMDAO/pyCycle | https://github.com/OpenMDAO/pyCycle | 有LICENSE.txt，**本次未能读正文，不猜** | Python（OpenMDAO） | 无 | README写primarily jet engine；例程为涡喷/涡扇 | README自身未给提交日 | `pip install om-pycycle`；依赖OpenMDAO | **非液体火箭循环** |
| Pyskyfire | https://github.com/ask-hovik/pyskyfire | MIT | Python | 无 | 再冷液体火箭+循环；热气用官方`cea`包；CoolProp冷却剂 | CHANGELOG `[0.3.0] - 30-08-2026` | Python≥3.12；`uv pip install pyskyfire` | 循环算法参考，不能C链接 |
| RocketCycles | https://github.com/janstruzinski/RocketCycles | GPL-3.0 | Python | 无 | 分级燃烧稳态循环；明确不做瞬态/管道摩擦等 | README未给发布日；仅见78 commits | pip git安装；nasaPoly、CoolProp/PyFluids、RocketCEA | 循环参考；GPL+Python |
| ESPSS/EcosimPro | 非GitHub产品页 | 非开源 | EcosimPro环境 | 不适用 | 官方写仅ESA成员国机构可用 | 检索摘要2025-04-21 | 商业/ESA渠道 | **不能当开源替代** |

## 1. NASA CEA v3（应深查）

官方仓库与文档把v3写成对原CEA的**完整重写**，目标是现代工程实践和多语言API。核心在 `source/`，可见 `cea.f90`、`equilibrium.f90`、`rocket.f90` 等Fortran文件。开发者指南写明：`source/` 是 Fortran 2008 实现；`source/bind/` 是 Python/C 绑定，经 Cython/C-API 包Fortran核心。
