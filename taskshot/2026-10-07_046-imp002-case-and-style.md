# 2026-10-07_046：成对算例文件与代码规范整合

- 关联任务：IMP-002
- 本轮请求/范围：按用户要求整理C职责与注释、明确成对算例、优化文档群与项目目录、改善代码交接与私有发布
- 起始状态：e0ecac4，CLI拆分与成对算例已在工作树（未提交），docs/coding-style.md不存在

## 实际检查和改动

CLI已拆分为 main/arguments/combustion_commands 与 adapters 的 combustion_report/propellant_case，先实测成对算例命令输出与参数CLI一致后才继续文档工作。新增[代码规范](../docs/coding-style.md)提炼自现有代码（分层、命名、契约注释、惯用模式、警告纪律），不引入外部风格。

关键注释补在非显然处：propellant_case.c的字段表offset链与身份重钉逻辑、combustion_commands.c的三种位置参数布局与布尔标志格、参数模式与算例模式的入口身份差异。契约本体仍在头文件，不重复复述。

文档群整顿：propellant-case-format.md按读者可用的字段表重写（保留全部事实与拒绝协议）；case-format.md、project-guide.md、CONTRIBUTING.md、README.md、handoff.md补入成对算例与代码规范入口；project-brief/verification/thermo-validation三个入链断裂的有效文档接入README职责表与project-map目录树。policy.json登记coding-style（tooling）与propellant-case-format（adapters）。

交付改进：DEMO_ARGS新增pair演示（成对算例文件），check_demo核对其schema/输入/差值与LIMITS；实测通过后清理临时文件。

## 验证结果

- `./build/release/rocketperf.exe study propellants --case cases/research/propellant_comparison.ini`返回正确JSON，差值isp_s=13.8534 s、thrust_n=−343.5653 N与ANA-012一致；check_demo('pair')实测PASS
- 一次质量运行FAIL原因是运行中继续编辑文档导致输入指纹变化（治理工具的正确防篡改行为），6组检查本身全PASS；文档收尾后重跑完整质量
- Release构建37组CLI测试、governance 20项测试通过

## 未解决和下一步

- 外部GitHub同步与Release发布需用户授权，本轮只完成本地交付能力
- DOC-001（研究报告与展示）仍为READY

## 交接更新

handoff复跑清单含成对算例；worknow/任务板由登记生成；policy.json已登记新文档。
