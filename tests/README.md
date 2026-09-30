# 验证入口

- `test_core.c`：解析Mach/性能参考、根求解错误与预算、输出事务性、42组连续/能量守恒、面积/背压缩放和参数边界。
- `test_cli.py`：Python标准库黑盒测试。检查参考JSON、UTF-8中文路径、BOM/CRLF、确定性、缺字段/重复/未知字段、非有限数、过膨胀拒绝、超长/NUL/文件限制、JSON转义和退出码。
- `reference/air_mach2.json`：独立从已知Me=2的闭式关系生成的数值，不由被测求根器生成。

入口为`pwsh -NoProfile -File ./scripts/test.ps1 -Configuration Debug`或Release。脚本会先重新构建再测试，全部通过后才写`build/<配置>/test-report.json`。报告关联被测二进制/构建清单哈希；重建后旧报告不能自动代表新二进制。

Linux可加`-Sanitize`检查地址/未定义行为；Windows路径明确不声称已支持该模式。CI已配置但本地测试不能代替真实CI运行。
