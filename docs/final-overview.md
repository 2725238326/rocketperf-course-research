# 课程收尾总览

整理日期：2026-10-13。此页回答交付前“有什么、怎么演示、还缺什么”；实际任务状态以[工作面](../worknow.md)、[任务板](tasks.md)和 `python tools/project.py doctor`为准。型号原文截止仍按2026-10-03/组员产品复核2026-10-06，接收文件日期不刷新在线事实。

## 现有成果

| 课程研究要求 | 可用内容 | 汇报时的边界 |
|---|---|---|
| 两型工作方案及优缺点 | [四级段研究](two-vehicle-study.md)、具名来源台账、[组员参数审阅](../调研/专题/RES-009_组员参数审阅.md) | 飞行批次、产品、试验产品分别写；长十乙一级后缀及二级循环未确认 |
| C计算性能 | C17物性、气态/液态HP、固定RP-1方法、冻结喷管、给定热状态外排及Q=0开式/补燃研究循环 | 九气相、恒密度泵、冻结涡轮/喷管；RP-1替代物不是国产煤油；算例不是真实性能卡 |
| 带计算的改进研究 | [喷管/背压/支路研究](improvement-analysis.md)、[入口响应](adiabatic-inlet-study.md)、[甲烷/RP-1同几何比较](propellant-method-comparison.md) | 同条件才谈收益；给出尺寸/流量代价，不算冷却、质量、侧载、寿命或真实改装量 |
| 方法验证与复跑 | [研究归档](../results/research/README.md)、[新循环软件/CEA对照](engine-cycle-validation.md)、统一质量入口 | 数值/软件状态核验，非独立实验或具名科学审查 |
| 同学新增交付 | [接收审阅](incoming-code-review.md)、原交接、两个一级算例/来源、给定温度补燃教学计账与菜单说明 | YF算例仍用甲烷化学代理；流量校准，原验证报告没有绑定重编译exe |

两型一二级已经各有明确研究落点，五个可运行车辆情景覆盖长十乙二级的两种待判拓扑。它们采用独立假设输入，不靠公开整箭推力反推真实单机。正式新循环归档为 `engine_cycles_v2_20261013`；本次接收复核归档为 `incoming_code_v1_20261013`。

## 三份循环结果不要混称

| 路线 | 实际回答的问题 | 演示位置 |
|---|---|---|
| 历史 `prescribed_thermal_cycle_v1` | 给定温度/压力后，外排、轴功与所需热量怎样计账 | `cycle prescribed cases/benchmarks/prescribed_cycle.ini` |
| 同学 `staged_thermal_cycle_v1` | 给定温度下把涡轮排气全回主室，质量与热量账怎样变化 | 原包独立exe + `cases/active-cases/cz10b-yf100k-staged.ini` |
| 当前 `adiabatic_single_shaft_cycle_v1` | 同基准入口/回流焓及元素在Q=0条件下，如何闭合开式/富氧补燃研究循环 | 当前exe + `cases/vehicles/*.ini`，菜单8 |

同学补燃例1396.050 kN/355.894 s是给定温度甲烷代理结果，不能和当前100 kg/s假设输入约285.50 kN/291.13 s拼成“修正后的真实YF性能”。输入、物理问题和燃料身份都不同。天鹊807.006 kN/352.820 s也只保留为标定的研究结果。

## 演示入口

新版本地运行包固定在 `build/delivery-final-overview-20261013/`。先检查其 `delivery-manifest.json`为PASS并运行：

```powershell
python tools/delivery.py verify --directory build/delivery-final-overview-20261013
```

完整解压 `rocketperf-windows-x64.zip`，双击 `rocketperf-run.bat`，进入C菜单后选择8，再选择1–5：朱雀三号遥一一、二级，长十乙一级RP-1补燃、二级开式待判、二级补燃待判。菜单输出来源角色、入口模型、温度、回流/外排、轴功、推力、比冲与限制。

从仓库运行相同内容：

```powershell
./build/release/rocketperf.exe interactive
./build/release/rocketperf.exe cycle adiabatic cases/vehicles/zq3_y1_stage1.ini --text
./build/release/rocketperf.exe cycle adiabatic cases/vehicles/cz10b_first_stage1.ini --text
./build/release/rocketperf.exe cycle adiabatic cases/vehicles/cz10b_first_stage2.ini --text
```

去掉 `--text`获得JSON供分析/保存，失败时保留退出码和stderr。菜单不伪造成功文件，也不默认覆盖研究归档。包内五例、双击启动器和成功/拒绝演示都绑定同一源码提交与已测二进制。

## 最终交付仍需完成的内容

1. [报告草稿](../deliverables/report.md)和[展示内容](../deliverables/presentation.md)统一采用上述模型/来源边界，把同学两例放在接收对照位置；解释为何现有资料不足以预测四级段真实性能。
2. 形成实际 `presentation.pptx`，确认[贡献表](../deliverables/contributions.md)的真实姓名/职责，并做10分钟演练。现有草稿、模板和方法通过状态不代替这三项事实。
3. 如要把同学新增室压、面积比、YF后缀、YF-219和比冲写成型号事实，按Grok流程取得原文并核对同批对象/工况；当前保留待核线索，现有假设研究可继续复跑。
4. 报告/PPT完成后按 `REL-001`验证最终课程提交清单及报告所用算例。此次产物是本地工程接收与演示更新，源码/运行包按清单固定；远端同步与发布另需明确授权。

剩余限制是同批性能卡、国产燃料、整机独立参考及实际汇报材料；无需为收尾重写已经可用的核心，或把未知量填成精确数值。完整接收结果和问题定位见[代码包审阅](incoming-code-review.md)。
