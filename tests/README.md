# 验证入口与覆盖

统一验收：`python tools/quality.py`。

| 层次 | 测试 | 覆盖 |
|---|---|---|
| 数学/核心 | test_core.c | 解析Mach与性能、连续/能量、缩放、求根失败、越域和有限数 |
| 物性 | test_thermo.c / test_thermo_data.py | 固定NASA9、形成焓、134状态软件参考、数据/温区/输出失败契约 |
| 燃烧/喷管 | test_combustion.c | TP/HP、元素与六条独立反应驻点、冻结喷管CEA对照、定cp解析极限和失败保持输出 |
| 外排/研究 | test_cycle.c / test_cycle_reference.py | 泵/涡轮解析极限、分流与两路推力、热量计账、C扫描比较量和归档篡改 |
| CEA证据 | test_cea_reference.py | 固定四卡、实际六状态TP、原输出trace/类型检查及重算哈希后仍拒绝数值错误 |
| 输出接口 | test_adapters.c | 写前拒绝非有限数/未终止文字/错误坐标或点数，控制字符转义 |
| 外部协议 | test_cli.py | 输入严格性、中文路径、BOM/CRLF、JSON/退出码、确定性 |
| 工程治理 | test_governance.py | 状态/依赖/WIP/负责人/事件/锁、契约修订、证据过期和架构边界 |
| 运行管理 | test_runner.py | schema与实际输入对应、不可变快照、超时/启动/复制/域失败、旧PASS拒绝 |
| 阶段交接 | test_handoff.py | 固定提交/已测程序、源码bundle、成功/失败演示、包清单和接收记录 |

核心解析参考来自已知Mach的闭式关系，不由待测求根程序产生。测试使用教学/研究输入，不充当真实发动机验证。
`test_cli.py` 是黑盒测试，必须由流水线传入已验证的可执行文件：

```powershell
python tools/pipeline.py test --configuration Debug
```

直接运行 `python -m unittest discover -s tests` 时，CLI测试会被明确跳过；这不会削弱流水线中的CLI测试。

治理测试使用build下的独立临时项目，运行管理测试留下results/local中的独立测试运行，不改原始资料。runner测试需要Release的新鲜已测构建，统一质量入口按正确顺序准备。

构建/测试报告记录RUNNING/PASS/FAIL与关联输入。历史Ubuntu WSL的ASan/UBSan仅覆盖当时基线，未覆盖新燃烧/冻结喷管；本轮只运行Windows。故意缺陷源码`fixtures/sanitizer_probe.c`不进入生产程序。远端CI尚未执行。

