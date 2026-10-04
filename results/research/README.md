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
