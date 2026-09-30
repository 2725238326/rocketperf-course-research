# 开发与维护

先读[AGENTS](AGENTS.md)、[当前工作](worknow.md)和[rules](rules.md)，再按任务读[工程设计](docs/engineering.md)。

## 本地最短检查

```powershell
pwsh -NoProfile -File ./scripts/test.ps1 -Configuration Debug
pwsh -NoProfile -File ./scripts/test.ps1 -Configuration Release
pwsh -NoProfile -File ./scripts/check-project.ps1
```

源码改动要运行受影响验证；核心算法变化须检查独立基准、守恒及边界，不仅检查输出文件存在。参数、模型或数据版本改变时保留差异解释，不直接改期望值来让测试变绿。

新适配器只能通过公共值类型/API使用核心；核心不得反向依赖CLI、文件路径、网络、绘图或环境变量。C源码采用4空格、UTF-8/LF；不得引入fast-math或静默浮点窄化。

测试fixture是教学/研究数据，不能借真实型号名字赋予其真实性。原始来源不做格式化或换行转换。提交前检查未包含密钥、build产物或临时运行文件；整项目发布许可尚未选择。

新增功能完成后更新任务板、worknow、handoff和一条有意义的taskshot。没有运行远端CI、CMake或某操作系统的测试时，明确写为未验证。
