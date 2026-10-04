# 实际状态与冻结喷管参考

分别保存合成循环实际温压/元素库存的TP参考，以及给定主室TP冻结/固定面积单喷管研究。每个版本保留CEA原始输入/输出、新C输出、比较和来源/构建哈希。原有10 MPa/HP/冻结四卡及旧归档保持字节和路径，不覆盖。

TP版本：[tp_v1_20261004](tp_v1_20261004/manifest.json)，六状态运行成功，126项打印/trace与关系比较通过。归档共39个文件（清单1个、声明文件38个），不含程序或数据库副本。

验证入口：`python tools/research_tp_reference.py verify results/research/reference-coverage/tp_v1_20261004`。
重新计算：完整质量通过后，`python tools/research_tp_reference.py archive results/research/reference-coverage/NEW-UNUSED-VERSION`。归档不携带CEA/C程序或重复的compiled物性库；重新计算另需既有固定CEA本机工具，离线读取归档不需外部求解器。

冻结版本：[frozen_v1](frozen_v1/manifest.json)，五个指定TP主室状态、A10/40及基准A10背压5 kPa，共11个固定喉面积C点、484条打印/关系检查。归档47文件含两份未改上游源码，证明参考工具确实支持指定TP；上游LICENSE/NOTICE原文保留在[物性来源](../../../data/thermo/manifest.json)指向的位置，不将源码快照编入C核心。

验证：`python tools/research_frozen_reference.py verify results/research/reference-coverage/frozen_v1`。新计算用`python tools/research_frozen_reference.py archive results/research/reference-coverage/NEW-UNUSED-VERSION`，要求新鲜已测Release和固定CEA本机环境；离线verify无需外部求解器，旧目录拒绝覆盖。

问题、打印精度和固定几何区别见[参考覆盖说明](../../../docs/research-reference-coverage.md)。本目录中的PASS只能证明这组受限气相状态/主喷管对照，不能证明液态/煤油、支路喷管、硬件或全循环性能。
