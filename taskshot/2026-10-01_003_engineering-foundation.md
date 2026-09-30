# 2026-10-01_003：工程质量基底与首个可运行功能

- 用户请求：基于工程质量的设计模式建立初期基底，补齐缺少内容。
- 任务：ENG-001；覆盖OPS-001和IMP-000的本地环境/教学基线范围。
- 状态：DONE。
- 范围：C17理想气体教学基线及工程支撑；没有更新在线型号事实、实现化学平衡/真实循环或移植第三方整库。

## 实施内容

1. 公共值类型/API、结构化状态、带容差和预算的通用二分求根；无文件I/O、堆分配或全局可变核心状态。
2. 理想定比热准一维喷管求解，显式SI输入输出；超声速分支、声速喉部、匹配/欠膨胀域。越域和无效浮点返回明确失败，失败不修改输出。
3. 严格版本化算例格式、JSON报告；拒绝重复/未知/缺字段、NUL、超长、无穷/非十进制/单位混写等。Windows UTF-8/UTF-16路径边界显式适配。
4. Mach2真空/背压两个教学输入、解析数值参考、C核心和Python标准库黑盒测试。
5. GCC Debug/Release脚本、构建/测试manifest、运行输入及二进制快照、SHA-256关联、失败归档和禁止覆盖。
6. CMake备用构建、Windows/Linux CI配置（本轮未执行）；本地Git main初始化、gitattributes保护原始证据字节、gitignore隔离构建/临时结果。
7. 工程设计、算例契约、基准、贡献和目录说明；更新入口、环境、规则、任务和交接状态。

## 实际验证

- GCC 14.2.0，严格`C17/-Wall/-Wextra/-Wpedantic/-Werror/-Wconversion/-Wshadow/-Wstrict-prototypes/-Wmissing-prototypes`。
- Debug及Release各190项C检查、10组CLI黑盒测试通过（包含多个失败子例）。
- 检查涵盖已知Me解析值、参考性能、42组连续/总焓守恒、几何/背压性质、求根失败/预算、NaN/Inf及大double有限检查、中文空格路径、BOM/CRLF、JSON转义及确定性。
- `run-case.ps1 -RunId foundation_air_mach2`生成成功运行；输入、实际二进制和输出哈希核对一致；重复RunId被拒绝且原结果未改变。
- `foundation_rejected_backpressure`记录明确越域失败，退出码4，保留manifest/stderr，没有成功result.json。
- Git已初始化main，build和results/local被忽略；对原始来源的Git text属性为unset，防止换行转换损坏旧哈希。没有提交和远端。
- 最终项目检查PASS：37份Markdown、106个本地链接、9个PowerShell脚本语法、43份来源快照哈希；3项历史缺失来源保留为known gaps。Debug/Release测试报告均与当前应用二进制及构建manifest哈希一致，并记录6份验证输入文件指纹。该检查不代替真实模型验证。

## 开发中发现并处理的问题

首轮编译时，截取`gcc --version`第一行的流水线提前关闭输出，影响退出码检查；已改为完整接收后再选首行。MinGW泛化isfinite宏触发double到float的严格转换诊断，改用有类型的有限值判断，保留警告策略。输入读取使用逐字节有界行读取，避免fgets/strlen默默忽略嵌入NUL。

以上是本次实际修正，不表示已完成形式化验证或穷举全部平台。

## 未完成范围

未执行CMake、远端CI、Linux sanitizer；未编译运行所调研的外部项目。未选择整项目对外许可证；无第三方核心代码移植。真实型号参数集、热化学、损失/冷却/循环、改进计算仍待后续任务。

## 接手

先用README命令构建/测试，阅读[工程设计](../docs/engineering.md)、[输入契约](../docs/case-format.md)和[基准](../docs/benchmarks.md)。随后推进RES-001/002/003，不重做一套空工程，不绕过越域检查把教学数值标成真实型号。
