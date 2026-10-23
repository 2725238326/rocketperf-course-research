# 第一阶段收官总览

更新：2026-10-23。用户确认第一阶段已收官。本阶段形成两型四级段的资料与参数边界、C17计算程序、条件性改进研究，以及报告、PPT、源码和Windows发布版四项材料。当前冻结交付入口为[20261020 v3提交归档](../deliverables/submission-20261020-v3/README.md)，不再按制作前的讲稿方案安排工作。

“收官”记录用户对本阶段的确认；课程平台上传、人工演练、接收者签收和GUI原生窗口视觉没有新增证据，不在此补称通过。任务事实仍由[任务板](tasks.md)维护；下一阶段范围待用户确定。

## 冻结交付与追溯

| 材料 | 第一阶段冻结入口 |
|---|---|
| 20页报告 | [v3报告PDF](../deliverables/submission-20261020-v3/04_作业报告/第五组_两型火箭动力系统性能研究报告.pdf)；可编辑源为[report-reviewed.typ](../deliverables/report_typst_v1/report-reviewed.typ) |
| 17页PPT | [提交PPTX](../deliverables/submission-20261020-v3/03_展示PPT/第五组_两型火箭动力系统性能研究.pptx) |
| C17源码 | [源码编译说明](../deliverables/submission-20261020-v3/01_程序源代码/README.md)；固定提交`3d4130c6db862c652bae7318cb85813ce0596d2e` |
| Windows发布版 | [运行说明](../deliverables/submission-20261020-v3/02_程序发布版/使用说明.txt)，包含控制台与GUI材料，GUI原生视觉仍单列待验 |
| 完整包与清单 | [四项ZIP](../deliverables/第五组_第一次大作业_分工更新版_20261020.zip)、[逐文件manifest](../deliverables/submission-20261020-v3/manifest.json) |

2026-10-23对162项材料逐文件复核哈希，并检查ZIP大小、SHA256、CRC及对应包内字节，全部通过。ZIP SHA256为`c6a29a5f411e10772a9d033845ac352819fc1e873a66ea2b1c3891bd56bce013`，大小11,977,891字节。此次复核不改写包或重做文档排版；源码独立重建5项C测试、每构建17项CLI演示、GUI桥接及前端检查沿用manifest绑定的原记录。

版本链见[074提交整理](../taskshot/2026-10-20_074-course-submission.md) → [075审查修订](../taskshot/2026-10-20_075-report-and-gui-review.md) → [076分工更新](../taskshot/2026-10-20_076-contributions-update.md)。v1、v2、原定稿、原始资料和研究归档保留；重新构建本机程序不改变旧包身份。本次入口整顿见[077收官记录](../taskshot/2026-10-23_077-phase-one-closeout.md)。

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

## 复跑入口

交付接收按v3包内说明编译或运行。历史`build/delivery-final-overview-20261013/`曾固定`59123e5`，后来本地缺失，只保留历史身份；不再把该临时目录或旧REL-001计划当作当前交付入口。

完整解压四项包，在发布版目录双击`rocketperf-run.bat`，进入C菜单后选择8，再选择1–5：朱雀三号遥一一、二级，长十乙一级RP-1补燃、二级开式待判、二级补燃待判。菜单输出来源角色、入口模型、温度、回流/外排、轴功、推力、比冲与限制。

从完整开发仓库复跑；这些开发工具不属于轻量源码提交包：

```powershell
python tools/quality.py
./build/release/rocketperf.exe interactive
./build/release/rocketperf.exe cycle adiabatic cases/vehicles/zq3_y1_stage1.ini --text
./build/release/rocketperf.exe cycle adiabatic cases/vehicles/cz10b_first_stage1.ini --text
./build/release/rocketperf.exe cycle adiabatic cases/vehicles/cz10b_first_stage2.ini --text
```

去掉 `--text`获得JSON，失败时查看退出码及诊断。交互菜单正常退出0不能证明菜单内每个算例都成功。交付复核读取包内INI、比较菜单数值与单独运行的JSON；源码与运行包的输入必须一致。固定物性与参考复算仍依赖仓库的版本化数据，运行exe只需包内文件和系统DLL。

## 历史任务与阶段安排

| 任务/事项 | 与收官产物的对应 | 保留边界 |
|---|---|---|
| DOC-001旧总任务 | 报告由DOC-005—008及SUB-002推进，PPT与四项交付由SUB-001/002记录 | 保留原负责人buaabw的BLOCKED及原验收契约；本次不替其补签演练或旧路径验收，不作为自动接续入口 |
| DOC-004旧讲稿补充 | 后续单人方案、17页PPT及正式提交已替代旧页码方案 | 经工具取消；不冒称原契约全部验收 |
| REL-001旧发布计划 | SUB-001/002及v3 manifest承担实际交付追溯 | 经工具取消，不再重复生成旧release-manifest路径 |
| GUI-001原生窗口 | 已有C桥接、前端及浏览器预览证据 | 原生窗口视觉仍待补；保留独立BLOCKED记录，不将浏览器截图作为原生验收 |
| 分工与课程现场 | [贡献表](../deliverables/contributions.md)同步2026-10-20用户确认版本；展示时限按15分钟、提问另计5分钟记录 | 不推断本人签署、人工计时、实际讲述效果或平台上传 |

## 后续工作的进入条件

第一阶段归档后不自动扩展模型或继续旧制作任务。若后续继续，应围绕用户新确定的问题领取任务，并先确认需要哪些新证据；GUI补验、接收者复跑、真实参数研究各自独立记录。用户新增的`Work2/`按第二次大作业原始资料单独保留，目录职责见[项目地图](project-map.md)。

若继续查型号参数，优先取得同批室压、主室O/F、喉面积/面积比和入口状态；每项须对应发动机版本、工况及原文。仅增加百科链接或更多推力量级不能补齐这组输入。既有型号原文核验截止2026-10-03，产品补充截止2026-10-06；未核的新线索见[代码包审阅](incoming-code-review.md)。
