# 项目登记

- `tasks.json`：任务契约、当前状态、负责人及带哈希链的历史事件。通过`tools/project.py task/add`操作，避免手工改状态。
- `modules.json`：模块职责、源文件、依赖边界和维护角色。GCC/CMake/架构检查共用。
- `policy.json`：目录与规范文档归属、WIP和Git约束。
- `technology.json`：TECH-001的技术选择摘要与实现状态；完整理由在docs/technology-stack.md。它不是完整传递依赖锁文件。
- `evidence/`：任务提交验收时复制的质量证据，保留原记录。
- `.locks/`：运行时OS锁文件，忽略版本控制；不是持久任务状态。

格式为schema_version=1。字段由工具显式校验；修改schema要同时修改验证器、迁移方式、测试和治理文档。哈希链提供意外改写检测，不替代身份认证或数字签名。

操作说明见[治理文档](../docs/governance.md)。
