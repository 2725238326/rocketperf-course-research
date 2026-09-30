# 维护与贡献

先读[Agent入口](AGENTS.md)、[治理规范](docs/governance.md)和对应[模块架构](docs/architecture/README.md)。

## 工作流

1. 查看任务契约，用工具领取；新增工作先定义产物和验收。
2. 在任务工作分支上修改代码/文档。原始资料只新增修订，不改旧字节。
3. 模块/API/数据语义改变时更新契约、登记和测试。架构变化重生成并视觉核对三视图。
4. `python tools/quality.py`；使用报告提交REVIEW并完成验收。
5. 记录taskshot和交接，审查diff，暂存完整可审查文件，运行提交检查，再做本地commit。

## Git护栏

```powershell
git config --local core.hooksPath .githooks
python tools/project.py check --staged
```

hook拒绝潜在密钥、临时产物、未纳入提交的必需文件、原始档案修改/删除和部分暂存引起的检查对象不一致。它不自动推送、不替代人工审查。不要用关闭hook掩盖错误。

## 代码与验证

C核心保持纯计算、显式SI与错误语义，禁止fast-math和隐式单位混用。Python工具使用标准库，PowerShell只作兼容入口。独立期望值不能通过运行被测程序来生成。

改变失败/并发行为需增加负向测试。参考值、物理假设和版本改变时解释原因，不直接改期望值让测试变绿。保留上游代码许可和变更边界，整项目发布许可由用户决定。

源码UTF-8/LF、4空格；原始证据由gitattributes禁用换行转换。实时Git状态由doctor读取，不在多份文档复制“尚无提交”等容易过期的描述。
