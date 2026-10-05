# 计算验证产物

这里保存实际C输出、CEA参考/原文副本、执行条件、二进制/构建/测试哈希和逐字段误差。必要的运行stdout/stderr和参考日志保留；exe和临时构建在被忽略的build目录。它不是目标型号性能或实验结果。

- `20261003_ch4_o2_frozen_v1`：首次-O2同条件对照。
- `20261003_ch4_o2_frozen_v2`：喷管回调状态显式初始化后的验证版本；保留v1，不覆盖旧运行。
- `adiabatic_inlet_v1`：同NASA9形成焓基准的显式气相HP、温度入口等价性、固定面积关系和失败协议；[范围/复跑](../../docs/adiabatic-inlet-validation.md)，不是液态或整机验证。

两版分别含TP、HP、A10与A40燃烧室冻结喷管。验证说明见[模型与容差](../../docs/thermo-nozzle-validation.md)。`tests/test_thermo_data.py`检查归档哈希、实际输出和逐字段比较；`tools/combustion_reference.py`复跑当前具体已测构建。历史源码哈希表示该次实际输入，不随未来修改伪造更新。
