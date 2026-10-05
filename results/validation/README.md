# 计算验证产物

这里保存实际C输出、CEA参考/原文副本、执行条件、二进制/构建/测试哈希和逐字段误差。必要的运行stdout/stderr和参考日志保留；exe和临时构建在被忽略的build目录。它不是目标型号性能或实验结果。

- `20261003_ch4_o2_frozen_v1`：首次-O2同条件对照。
- `20261003_ch4_o2_frozen_v2`：喷管回调状态显式初始化后的验证版本；保留v1，不覆盖旧运行。
- `adiabatic_inlet_v1`：同NASA9形成焓基准的显式气相HP、温度入口等价性、固定面积关系和失败协议；[范围/复跑](../../docs/adiabatic-inlet-validation.md)，不是液态或整机验证。
- `liquid_anchor_v1`：固定CH₄(L)111.643 K/O₂(L)90.170 K反应物HP、三组O/F/两种面积比、几何关系与拒绝协议，21次C/6次新CEA；[范围/复跑](../../docs/liquid-anchor-validation.md)，不含液体EOS/泵/压力修正或真实型号。
- `liquid_table_v1`：C17连续单相密度/化学焓查询的6次成功与16次拒绝，带具体Release构建/测试身份；[接口与核验](../../docs/liquid-feed-validation.md)。不包含HP、泵或循环耦合。

两版分别含TP、HP、A10与A40燃烧室冻结喷管。验证说明见[模型与容差](../../docs/thermo-nozzle-validation.md)。`tests/test_thermo_data.py`检查归档哈希、实际输出和逐字段比较；`tools/combustion_reference.py`复跑当前具体已测构建。历史源码哈希表示该次实际输入，不随未来修改伪造更新。
