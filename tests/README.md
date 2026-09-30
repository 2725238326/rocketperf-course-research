# 验证入口与覆盖

统一验收：`python tools/quality.py`。

| 层次 | 测试 | 覆盖 |
|---|---|---|
| 数学/核心 | test_core.c | 解析Mach与性能、连续/能量、缩放、求根失败、越域和有限数 |
| 外部协议 | test_cli.py | 输入严格性、中文路径、BOM/CRLF、JSON/退出码、确定性 |
| 工程治理 | test_governance.py | 状态/依赖/WIP/负责人/事件/锁、契约修订、证据过期和架构边界 |
| 运行管理 | test_runner.py | schema与实际输入对应、不可变快照、超时/启动/复制/域失败、旧PASS拒绝 |

核心解析参考来自已知Mach的闭式关系，不由待测求根程序产生。测试使用教学/研究输入，不充当真实发动机验证。

治理测试使用build下的独立临时项目，运行管理测试留下results/local中的独立测试运行，不改原始资料。runner测试需要Release的新鲜已测构建，统一质量入口按正确顺序准备。

构建/测试报告记录RUNNING/PASS/FAIL与关联输入；只有新鲜完整证据可用于任务验收。Linux sanitizer与远端CI需真实执行后才可宣称通过。
