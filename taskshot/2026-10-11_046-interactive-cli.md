# CLI交互模式、人读输出与命令编排重构

日期：2026-10-11，IMP-003；起始27e29fa。针对软件本体与交互偏弱的评审意见补课，不新增物理模型。

新增`src/cli/interactive.c`：`rocketperf interactive`或控制台无参运行进入菜单，覆盖连续液态/锚点/RP-1/气态四种推力室入口、甲烷-RP-1同条件对比、气态HP、NASA9物性、液体单相查表和L0理想喷管。逐项提示参数名/单位/默认值，回车取默认，非法数值重提示，q取消，EOF安全退出；求解复用既有公共C接口，不绕开域检查。非TTY无参仍返回2，保持既有契约。Windows下交互与人读路径先切控制台UTF-8代码页，退出恢复。

新增`src/adapters/text_report.c`：中文带单位的人读文本报告（UTF-8），按近似终端宽度对齐标签，覆盖燃烧室组分/诊断、喉部出口站、固定几何、L0结果、液体入口、物性与成对对比表；每条结果保留方法限制说明。`run CASE.ini --text`、`study propellants ... [--text]`和`--case ... --text`改出人读输出，JSON契约不变。

`rocketperf cases`列出五个内置算例及运行方式。`--help`重构为分组命令清单并以Usage开头，补回此前遗漏的RP-1/交互说明。

tests/test_cli.py新增交互脚本会话（管道输入）、`--text`、cases、help分组的回归测试；Debug/Release各41组CLI、core 207、adapters 29、thermo 8978、combustion 3894、cycle 353通过。模块登记同步（cli+interactive、adapters+text_report，契约注明交互与人读输出），四张架构SVG重生成并sharp渲染逐图核对无遮挡裁切。docs/project-guide.md运行章节补交互/text/cases说明。

治理工具修正：Debug测试套件已超时quality.py单步240 s上限（实测约265 s），单步超时放宽至900 s；此前统一入口并非代码失败而是超时误报。

边界：交互模式是人读入口，不是新模型；JSON仍为机器契约；循环算例只列运行方式不进菜单；展示报告仍待DOC-001。
