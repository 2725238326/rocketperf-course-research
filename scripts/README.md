# 兼容脚本入口

PowerShell入口保留原用法，行为统一实现于tools/，避免两份流程逐渐漂移：

| 入口 | 实现 |
|---|---|
| build.ps1 | tools/pipeline.py build |
| test.ps1 | tools/pipeline.py test |
| run-case.ps1 | tools/pipeline.py run |
| check-project.ps1 | tools/project.py check |
| check-powershell.ps1 | PowerShell语法解析，只读检查 |

推荐统一验收：`python tools/quality.py`。支持参数与运行语义见[环境](../docs/environment.md)和[治理规范](../docs/governance.md)。

调研脚本仍位于调研/scripts/；检索凭据不会进入构建或运行记录。
