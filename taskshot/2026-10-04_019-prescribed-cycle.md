# 给定热状态的外排循环

执行日期：2026-10-04（北京时间）。任务MOD-003；Windows MinGW主线，不推送远端。

## 产物

`include/rocketperf/cycle.h`与`src/cycle/`实现恒密度泵、NASA9温变冻结涡轮、单轴支路分配、主/支喷管和三类残差。严格输入/报告在`src/adapters/cycle_case.c`；与旧L0共用有限十进制、NUL/长度和UTF-8路径工具，不改变旧schema。

合成输入是`cases/benchmarks/prescribed_cycle.ini`。`rocketperf cycle prescribed CASE.ini`实际输出泵/涡轮/喷管状态、两路分流、推力和所需热交换；`tools/pipeline.py run --model prescribed-cycle`保存已测构建、输入/结果及哈希，并先重算计账方程。固定结果为`results/validation/prescribed_cycle_v1_20261004/`。

## 修正与失败

- 返回流量未混入主室化学库存，原设计不成立；v1改为明确拒绝所有非零回流字段，保留未来扩展边界而不称补燃已实现。
- 第一轮184项循环测试有1项失败：零支路O/F用了浮点严格相等。改为1e−14容差，重跑通过，原失败日志留在`build/artifacts/debug/3de020e633324e118a128a974d7c18c8/`。
- 增补源码指纹和归档后，旧Release证据不再新鲜，单独runner执行被拒绝；最终由完整质量入口重建/测试后验收，不回退旧PASS。
- 首次全量验收发现旧物性资料测试把所有validation目录当作燃烧参考。新增按kind分派燃烧/循环核验，未知kind仍失败；旧失败保留在`build/artifacts/debug/7fcf169fdc0b41d0b055c66b0305f310/thermo-data-test.log`。
- 定位补丁入口时误调用系统bash，触发WSL启动并报错；停止该路径，没有用WSL编译/测试项目或改配置。随后使用Windows本地补丁入口与MinGW/CMake。
- 前序Grok两次HTTP 502没有有效证据；固定Pyskyfire源码由HTTP逐文件哈希核验，没有浏览器UI检索，也没有暴露凭据。

## 实际验证

Windows GCC14.2 Release通过core 207、adapters 29、thermo 1175、combustion 2512、cycle 241项检查和CLI 22组；CMake/Ninja Release通过6/6 CTest。初步Debug的184项循环检查也已运行，最终Debug/Release以本次质量快照为准。运行计账重新核对86条方程，16种篡改JSON反例必须失败。

16个生产C源文件以相同严格警告加`-fanalyzer`静态分析通过，实际日志/输入哈希在`build/static-mod003/manifest.json`。这不是完整输入空间无错误的证明；新增循环没有ASan/UBSan插桩证据。

架构三视图按模块登记重生成；功能图实际渲染至`build/architecture-components.png`并视觉核对，文字/线条/边界完整。循环保留prototype，给定热状态与非零回流限制明确可见。

## 数值与解释

合成输入得到泵功1.137201608 MW、涡轮轴功1.207580640 MW、外排支路0.674224777 kg/s、整机推力296254.198769 N、等效比冲302.095209647 s。它维持指定温度需要发生器约2.08 MW热输入和主室约193.65 MW热排出；不是绝热真实发动机循环，不填入两型性能表。

完整边界与命令见[循环说明](../docs/cycle-validation.md)。本轮不做PPT/报告，不处理液态真实物性、回流混合、冷却、泵图谱、瞬态、凝聚相/积碳或寿命。下一步按工作面推进改进代价、敏感性与可用研究工况。
