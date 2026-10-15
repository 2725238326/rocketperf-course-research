# 课程收尾总览

更新：2026-10-15。课程提交包括源码、运行版、PPT和报告，展示时间为10月16日；用户最新确认展示15分钟、提问另计5分钟（原始存档的10分钟保持历史原文）。DOC-003提供讲稿、讲解思路、模板具体选页和逐页替换指导，由小组组合页面后再共同优化；当前不代做最终PPT。具名贡献与人工实测演练仍待本人完成。任务状态见[任务板](tasks.md)。

## 现有成果

| 课程研究要求 | 可用内容 | 汇报时的边界 |
|---|---|---|
| 两型工作方案及优缺点 | [四级段研究](two-vehicle-study.md)、具名来源台账、[组员参数审阅](../调研/专题/RES-009_组员参数审阅.md) | 飞行批次、产品、试验产品分别写；长十乙一级后缀及二级循环未确认 |
| C计算性能 | C17物性、气态/液态HP、固定RP-1方法、冻结喷管、给定热状态外排及Q=0开式/补燃研究循环 | 九气相、恒密度泵、冻结涡轮/喷管；RP-1替代物不是国产煤油；算例不是真实性能卡 |
| 带计算的改进研究 | [喷管/背压/支路研究](improvement-analysis.md)、[入口响应](adiabatic-inlet-study.md)、[甲烷/RP-1同几何比较](propellant-method-comparison.md) | 同条件才谈收益；给出尺寸/流量代价，不算冷却、质量、侧载、寿命或真实改装量 |
| 方法验证与复跑 | [研究归档](../results/research/README.md)、[新循环软件/CEA对照](engine-cycle-validation.md)、统一质量入口 | 数值/软件状态核验，非独立实验或具名科学审查 |
| 同学新增交付 | [接收审阅](incoming-code-review.md)、原交接、两个一级算例/来源、给定温度补燃教学计账与菜单说明 | YF算例仍用甲烷化学代理；流量校准，原验证报告没有绑定重编译exe |

五个车辆情景使用研究假设。朱雀三号二级和长十乙二级开式情景的数值输入相同，不能按两个独立物理验证点计数；长十乙二级的开式/补燃两例还改变了泵后压力和预燃输入，差值不能单归因于循环。输入、闭合方程和两个一级情景结果现列于[报告第7.6节](../deliverables/report.md)。正式循环归档为 `engine_cycles_v2_20261013`，接收复核为 `incoming_code_v1_20261013`。

## 计算结果的用途

| 路线 | 实际回答的问题 | 演示位置 |
|---|---|---|
| 历史 `prescribed_thermal_cycle_v1` | 给定温度/压力后，外排、轴功与所需热量怎样计账 | `cycle prescribed cases/benchmarks/prescribed_cycle.ini` |
| 同学 `staged_thermal_cycle_v1` | 给定温度下把涡轮排气全回主室，质量与热量账怎样变化 | 原包独立exe + `cases/active-cases/cz10b-yf100k-staged.ini` |
| 当前 `adiabatic_single_shaft_cycle_v1` | 同基准入口/回流焓及元素在Q=0条件下，如何闭合开式/富氧补燃研究循环 | 当前exe + `cases/vehicles/*.ini`，菜单8 |

同学补燃例1396.050 kN/355.894 s是给定温度甲烷代理结果，不能和当前100 kg/s假设输入约285.50 kN/291.13 s拼成“修正后的真实YF性能”。输入、物理问题和燃料身份都不同。天鹊807.006 kN/352.820 s也只保留为标定的研究结果。

## 演示入口

历史运行包 `build/delivery-final-overview-20261013/`曾固定源码提交 `59123e5`，但2026-10-15审核时本地目录缺失，不能当作当前可用包。最终定稿后由REL-001重新冻结并核验本轮包；以下仅是旧包存在时的核验方式：

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

去掉 `--text`获得JSON，失败时查看退出码及诊断。交互菜单正常退出0不能证明菜单内每个算例都成功。交付复核读取包内INI、比较菜单数值与单独运行的JSON；源码与运行包的输入必须一致。固定物性与参考复算仍依赖仓库的版本化数据，运行exe只需包内文件和系统DLL。

## 交付前的具体检查

| 工作 | 完成时应看到什么 | 未满足时怎样处理 |
|---|---|---|
| 报告技术审稿 | 每组结果紧邻输入/单位/出处；流程图对应真实接口；改进讨论说明固定量、变化量和代价 | 无原文的型号数字撤下；保留可复跑的假设算例。当前内容见[报告](../deliverables/report.md) |
| PPT与讲稿 | [逐页制作指南](../deliverables/ppt-structure.md)给定原模板复制页码与替换内容，小组先组合12页正文；A讲1–6，B讲7–12，预算13:45含100秒演示，提问另计5分钟 | 当前PPT尚待小组组合与优化；按[时间表](../deliverables/timing-chart.md)人工实测，组号、姓名与贡献待本人填写 |
| 人员贡献 | 真实姓名、实际产物、本人确认 | [贡献表](../deliverables/contributions.md)继续标待确认；不能由文件作者或AI推测 |
| 最终四件套 | 报告、PPT、源码和运行版齐全；固定提交，报告引用算例在交出包内复跑 | 由REL-001验收；本地工程包不能单独代表课程交付完成 |

若继续查型号参数，优先取得同批室压、主室O/F、喉面积/面积比和入口状态；每项须对应发动机版本、工况及原文。仅增加百科链接或更多推力量级不能补齐这组输入。既有型号原文核验截止2026-10-03，产品补充截止2026-10-06；未核的新线索见[代码包审阅](incoming-code-review.md)。
