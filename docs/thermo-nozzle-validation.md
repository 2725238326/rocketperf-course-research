# 受限燃烧平衡与温变冻结喷管

## 接口与适用域

模型采用固定九种中性理想气体：H2、O2、H2O、CO、CO2、CH4、H、O、OH，元素顺序为C/H/O。入口只接受气态CH4/O2，入口焓由同一NASA9数据库计算；液态入口显式拒绝。TP限制在1000–6000 K；冻结混合物和喷管只在所有存在物种的NASA9温区内计算。不求凝聚相、离子或碳沉积，不能据气相解判断相态稳定或结焦。

软件数值护栏为p=100–10⁹ Pa、O/F=0.1–20；它们不是经实验认证的理想气体适用域，尤其高压不能据此声称真实气体效应可忽略。守恒测试网格为p=0.1/1/10 MPa、O/F=2/3.4/5、T=1000/2000/4000/6000 K；CEA喷管对照现含100 bar、O/F=3.4的HP族，以及50 bar、给定3300 K及温度/O/F邻域的五个TP冻结状态，见[实际覆盖](research-reference-coverage.md)。

公共接口位于`include/rocketperf/combustion.h`和`include/rocketperf/frozen_nozzle.h`。核心无文件、网络、Python/Fortran依赖或堆分配。输出只在求解和残差验收全部通过后赋值；参数错误、温区/相态越域、夹逼失败、迭代耗尽和数值失败分别返回显式状态。

## 方程与数值策略

TP用理想气体Gibbs驻点及元素守恒。令元素势为λ、总量为N：

`ln(n_i) = ln(N) + Σ(a_ei λ_e) − g_i°/(R_u T) − ln(p/p°)`。

求解三条元素约束和`Σn_i=N`。残差采用log-sum-exp表示的比值对数，避免微量物种和低温自由能导致指数溢出；4×4线性子问题用带主元消元，Newton步有上限及回溯。从6000 K分段下降到目标温度，保持正组分，不把不收敛截断成成功。元素库存以1 kmol CH4归一化，不把归一化量当作kmol/kg。

HP在用户给定温度夹逼区间内反复调用TP，外层二分求`h_products − h_feed=0`，最终独立检查元素残差、平衡残差与焓残差。形成焓已包含在NASA9系数中，不重复加热值。

混合物按质量加权求cp和h，熵含理想混合及压力项。冻结喷管保存燃烧室组分；等熵压力由`ln(p/p_c)=(s°(T)−s°(T_c))/R_mix`得到，速度由`u²=2(h_c−h)`得到。喉部求`u²=γ(T)R_mix T`，出口求`G_t/G_e=A_e/A_t`，取低温超声速支。结果另检查连续、能量、熵和声速残差。有效排气速度包含压力推力，不把速度单位m/s写成比冲秒。

`rp_nozzle_solve_frozen_fixed_area`复用冻结核心，固定喉面积后由阻塞通量求流量，返回出口面积、推力和比冲。它只负责单喷管，不做泵/轴功/分流/液态入口闭合。面积非正或非有限、派生尺寸/性能上溢或下溢为零、背压越域、根失败均保持输出不变。CLI的`frozen-tp`先求指定TP平衡再冻结；原`frozen`仍先求气态入口HP。

## 验证记录

2026-10-03实际运行：Windows GCC14.2.0，C17；日常Debug/Release分别使用-O0/-O2，独立CMake Release使用-O3。参考来自固定CEA v3.3.4的九物种气态CH4/O2卡，见[复现说明](reference-reproduction.md)。原始CEA输入/输出未改动，C输出独立归档于[验证版本v2](../results/validation/20261003_ch4_o2_frozen_v2/manifest.json)。v1保留最初-O2产物；v2对应喷管回调显式初始化修正后的源码与构建。

固定条件：Pc=10⁷ Pa、O/F=3.4、气態CH4/O2各298.15 K，燃烧室无限截面、无入口动能。TP另指定3000 K；喷管固定燃烧室组分，环境压力为0。

| 量 | C结果 | CEA打印值 | C−CEA |
|---|---:|---:|---:|
| HP燃烧室温度 K | 3673.614568 | 3673.61 | +0.004568 |
| 冻结c* m/s | 1839.387209 | 1839.39 | −0.002791 |
| A10出口温度 K | 1691.557876 | 1691.56 | −0.002124 |
| A10真空有效排气速度 m/s | 3192.263180 | 3192.26 | +0.003180 |
| A40出口温度 K | 1173.071439 | 1173.07 | +0.001439 |
| A40真空有效排气速度 m/s | 3435.407478 | 3435.41 | −0.002522 |

HP实际焓残差为−0.004123 J/kg。对照使用打印精度感知的绝对容差：HP温度0.02 K、冻结温度0.03 K、c*/有效排气速度0.03 m/s、组分2×10⁻⁶、分子量5×10⁻⁵ kg/kmol。CEA未打印的CH4按trace=10⁻⁸上限检查，不填零后假称组分相等。平衡喷管只作不同化学路径参考；沿程平衡A40的3696.84 m/s不是本模型应当达到的目标。

### 实际覆盖

以下数量是2026-10-03该版本的历史记录；2026-10-04的新增固定面积、缩放、压力推力扣减及输出保持反例，以当轮质量报告和[执行快照](../taskshot/2026-10-04_024-fixed-area-nozzle.md)为准，不倒改历史计数。

`tests/test_combustion.c`执行2512项检查：36个TP状态和9个HP状态的独立元素比/质量守恒、六条反应的化学势驻点；混合物dh/dT与ds/dT；与CEA的TP/HP/A10/A40对照；冻结组分不变；喉部声速与连续/能量/熵残差；匹配背压及A=1；固定原子H的定cp解析Mach 2极限。NaN/Inf、负量/错误归一化、液相、温区越界、背压越域、未夹逼和预算耗尽明确失败，失败时输出哨兵不变。

残差门槛：平衡对数残差≤10⁻¹⁰、元素相对残差≤2×10⁻¹⁰、HP焓差≤0.01 J/kg、喷管连续/声速相对残差≤10⁻⁸、能量差≤10⁻⁵ J/kg、熵差≤10⁻⁷ J/(kg·K)。CLI实际执行18组，零跳过；包含将NaN、错误冻结位置、改变组分、错误单位、虚假模型/输入和守恒错误包装为成功的反例。五组CMake CTest通过。GCC -fanalyzer检查12个生产C源，无诊断。

首次CMake -O3编译曾报喷管回调局部state可能未初始化；改为显式零初始化后通过，没有关闭警告或-Werror。失败及重跑见[执行快照](../taskshot/2026-10-03_018-combustion-frozen-nozzle.md)。这些检查是软件/数学参考验证，不是实验验证、独立人员审查或真实发动机认证。

### 复跑

```powershell
python tools/quality.py
./build/release/rocketperf.exe combustion tp 3000 10000000 3.4 298.15 298.15
./build/release/rocketperf.exe combustion hp 10000000 3.4 298.15 298.15
./build/release/rocketperf.exe combustion frozen 10000000 3.4 298.15 298.15 40 0
./build/release/rocketperf.exe combustion frozen-tp 3300 5000000 3.436135058 298.15 298.15 10 0 0.03388974484581763
python tools/combustion_reference.py
python tools/research_frozen_reference.py verify results/research/reference-coverage/frozen_v1
```

参考工具从新鲜已测manifest找到具体二进制，复制二进制与参考manifest到唯一build目录，记录stdout/stderr、输入命令、哈希、逐字段差值与PASS/FAIL。`--archive-id NEW-ID`新增results/validation版本；已有目录拒绝覆盖。Python只组织运行和比对，不求燃烧或喷管。任意研究输入的通用运行归档、液態入口/煤油替代物、损失/循环/冷却和更广泛参考仍是后续工作。
