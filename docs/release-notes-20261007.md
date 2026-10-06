# Rocketperf Windows与纯C源码阶段交付

包含纯C源码ZIP、Windows x64运行ZIP、详细项目解读、固定提交清单和SHA256校验和。完整研究资料、原文快照、开发工具和历史记录保留在本私有仓库。

源码ZIP不含Python/Fortran文件，通过Windows CMake/GCC构建并运行五个C测试。运行ZIP包含已测exe、教学喷管/外排循环/RP-1及拒绝算例的输入输出和核验日志，直接运行无需Python或编译器。

固定RP-1公共入口支持10 MPa、O/F=2.2–4.0、RP-1=298.15 K和O2(L)=90.170 K；连续甲烷入口及冻结喷管、给定热状态循环已有方法参考。发布二进制、源码包和提交身份见delivery-manifest.json；下载后先核对SHA256SUMS.txt。

本版本是阶段软件交付。真实型号完整性能卡、国产煤油批次、泵后/完整循环、冷却/寿命、最终报告和PPT仍有未完成项。项目自有代码尚未选择公开许可证，NASA CEA/CoolProp数据许可声明随包保留。
