# 工程脚本

从项目根目录运行，PowerShell 7。脚本使用参数数组调用编译器/程序，不拼接shell命令。构建仅写build，运行记录写results/local，不删除原始材料。

| 脚本 | 作用 |
|---|---|
| build.ps1 | GCC C17严格警告，Debug/Release，生成应用和核心测试及构建manifest |
| test.ps1 | 先构建，再运行C核心与Python黑盒测试；成功后写测试报告 |
| run-case.ps1 | 先构建，再执行输入快照/二进制快照，保存结果及哈希；RunId不能覆盖 |
| check-project.ps1 | 文档链接、PowerShell语法、来源文件哈希等离线检查，不运行物理验证 |

Grok/原始来源下载脚本仍在`调研/scripts/`，不与工程运行混用。完整环境信息见[环境说明](../docs/environment.md)。
