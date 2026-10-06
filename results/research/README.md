# 研究计算档案

## 2026-10-07 甲烷与固定RP-1成对方法

[propellant_comparison_v1](propellant_comparison_v1/manifest.json)保存57次C运行和8张新CEA卡：三个O/F情景、A10/A40与0/5/100 kPa背压共18个成对点，并逐点单独复跑两方法。15对成功、3对越域；共同几何/差值由C接口返回，1410项参考/关系比较。分析和SVG见[研究说明](../../docs/propellant-method-comparison.md)。复核：`python tools/propellant_comparison.py verify results/research/propellant_comparison_v1`。

## 2026-10-06 固定RP-1产物比较

[kerosene_products_v3_20261006](kerosene_products_v3_20261006/manifest.json)保存15张新CEA输入/输出及日志，6个C燃烧室点（5成功、1数值失败）和O/F=2.6的两套固定面积喷管。固定10 MPa，RP-1/O₂(L)指定焓；比较九气相与扩展中性产物，保留富燃料凝聚碳和温度探查行为。方法边界见[RES-008](../../调研/专题/RES-008_煤油计算边界.md)。

```powershell
python tools/kerosene_reference.py verify results/research/kerosene_products_v3_20261006
```

研究驱动严格编译C17，生产内核未新增燃料接口；Python只编排和复算。C构建清单记录驱动/核心输入哈希，运行时HEAD为此前提交，后续提交固定本批次源码；不能把此前HEAD单独当作驱动身份。中间失败/纯CEA尝试保存在build，不作为正式研究版本。

只保存选定且可复验的研究版本；试跑在`results/local/`，构建/临时文件在`build/`。原始课件、资料与固定参考不移到这里。每个版本保留输入、stdout/stderr、结果、构建/测试/运行清单和哈希；不携带重复exe。

## 2026-10-04 给定热状态扫描

[prescribed_cycle_scan_v1_20261004](prescribed_cycle_scan_v1_20261004/manifest.json)：相同合成输入/物性数据，8个白名单输入轴，以及面积比20/40的背压扫描，共10份、39点。31成功、8模型域排除；数学/计账检查不证明真实发动机性能。

清单如实记录运行时`source_dirty=true`：当时从未提交的新增源码构建，HEAD是此前基线，不能把该HEAD单独当作运行源码身份。精确构建输入哈希在每份build-manifest，新增源码随本轮Git提交固定；归档不事后改写它的历史。

```powershell
python tools/cycle_study.py verify results/research/prescribed_cycle_scan_v1_20261004
python tools/pipeline.py run --case cases/benchmarks/prescribed_cycle.ini --cycle-field main_area_ratio --cycle-values 10,20,40
```

重建整个研究须先完整质量通过，再运行`python tools/cycle_study.py archive results/research/NEW-UNUSED-ID`。新ID必须不存在；生成先在build完成再一次发布，避免归档中途改变已测输入指纹。新归档纳入测试身份后重新验收；不能覆盖旧版本。

分析与外推限制见[研究说明](../../docs/improvement-analysis.md)。固定四工况的新C复跑在[方法归档](../validation/ana002_method_reference_20261004/manifest.json)，不与循环扫描混称同条件整机参考。原CEA卡与原始输出保持字节；本机上游四卡也重新运行。

## 2026-10-04 实际研究状态与冻结喷管参考

[参考入口](reference-coverage/README.md)从上面保存的循环状态取主室/发生器及温度、总体O/F邻域条件，新运行固定CEA与已测C程序。TP六状态、126项比较；冻结五组主室状态、11个固定面积C点、484条打印/关系检查。详细差值和打印精度在[参考覆盖说明](../../docs/research-reference-coverage.md)。这补上具体状态的热化学/主喷管对照，不等于支路或整个循环已同条件外部验证。

## 2026-10-04 入口焓与密度诊断

[thermal_boundary_v1](thermal_boundary_v1/manifest.json)保存七份实际C运行：基线、两种焓各±100 kJ/kg、两种密度各×0.9。每次只变一个输入；每点132条状态检查，另复核热量/焓率与泵功/分流的跨工况解析关系。共用构建和测试清单，严格文件清单、输入、stdout/stderr及身份校验；没有重复exe。

```powershell
python tools/thermal_boundary.py verify results/research/thermal_boundary_v1
```

步长只是诊断情景，不是有依据的液体物性范围。焓变化在给定温度模型中不改变推力，密度变化影响泵功和分流；结果和新的模型契约见[热边界审阅](../../docs/research-thermal-boundary.md)。`source_dirty=true`和此前HEAD保持历史原样，实际C源码由构建输入哈希固定。重建使用已测Release与新目录，不能覆盖旧版本。

## 2026-10-05 固定几何气态入口焓与混合比

[adiabatic_inlet_response_v1](adiabatic_inlet_response_v1/manifest.json)保存12种入口条件、两套分别固定几何的真空喷管：51次C运行（含5次预期拒绝）、12次固定CEA新运行和24个几何点。Pc=10 MPa、At=0.01 m²，A10/A40各自固定Ae；气态入口温度对应同NASA9形成焓，不是液态输入。

```powershell
python tools/adiabatic_study.py verify results/research/adiabatic_inlet_response_v1
python tools/adiabatic_study.py plot results/research/adiabatic_inlet_response_v1
```

[分析与SVG](../../docs/adiabatic-inlet-study.md)显示升比冲不等于升推力，O/F轴也未证明连续最优值。Python只编排、归档、复算保存状态和呈现，C17完成物性/HP/喷管求解。原卡、原输出、运行流、上游/构建/测试身份完整保存，运行dirty状态不倒改；归档前的测试清单不替代归档后的完整验收。新版本另取未用目录，旧档案保持字节。

## 2026-10-05 连续单相液体参考

[liquid_feed_reference_v1](liquid_feed_reference_v1/manifest.json)保存固定 CoolProp 7.1.0 HEOS 的407节点、700内部点、107饱和状态对、14理想项温度点和24查询。假设矩形为 CH₄ 100–140 K、O₂ 80–110 K、P=1–20 MPa；不作为型号参数。摩尔化学焓按 CEA/NASA9 在298.15 K的理想零点对齐，保留残余焓和温区cp差异。

```powershell
python tools/liquid_feed.py verify results/research/liquid_feed_reference_v1
```

复核使用保存的原文和标准库解析系数计算，不需要安装 CoolProp。实际插值误差与质量口径见[契约](../../docs/liquid-feed-contract.md)及[专题](../../调研/专题/RES-007_连续液体基准.md)。原软件输出保留，软件对照/同源系数复算不能替代实验。
