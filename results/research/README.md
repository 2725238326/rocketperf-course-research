# 研究计算档案

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
