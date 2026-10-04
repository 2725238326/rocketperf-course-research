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

## 2026-10-04 实际研究状态TP参考

[六状态归档](reference-coverage/README.md)从上面保存的循环状态取主室/发生器及温度、总体O/F邻域条件，新运行固定CEA与已测C程序。六状态、126项比较通过，详细差值和打印精度在[参考覆盖说明](../../docs/research-reference-coverage.md)。这补上具体状态的热化学对照，不等于冻结喷管或整个循环已同条件外部验证。
