# 实际状态TP参考

每个新版本保存六个来自合成循环的温压/元素库存条件，以及CEA原始输入/输出、新C输出、比较和来源/构建哈希。原有10 MPa/HP/冻结四卡保持字节和路径，不覆盖。

本轮固定版本：[tp_v1_20261004](tp_v1_20261004/manifest.json)，六状态运行成功，126项打印/trace与关系比较通过。归档共39个文件（清单1个、声明文件38个），不含程序或数据库副本。

验证入口：`python tools/research_tp_reference.py verify results/research/reference-coverage/tp_v1_20261004`。
重新计算：完整质量通过后，`python tools/research_tp_reference.py archive results/research/reference-coverage/NEW-UNUSED-VERSION`。归档不携带CEA/C程序或重复的compiled物性库；重新计算另需既有固定CEA本机工具，离线读取归档不需外部求解器。

问题、打印精度和固定几何区别见[参考覆盖说明](../../../docs/research-reference-coverage.md)。本目录中的PASS只能证明这组受限气相状态对照，不能证明液态/煤油、两路喷管、硬件或全循环性能。
