# 项目交接

从[当前工作面](worknow.md)读取任务，运行`python tools/project.py doctor`核对Git实况。领取和验收命令见[治理说明](docs/governance.md)。

2026-10-20 DOC-008按用户明确确认调整报告分工：报告撰写和核心算法归纪博闻，何明轩改为补燃循环介绍与分析，宋俊辉保留结构整理和校对。表后总结同步，当前提交入口为[分工更新版](deliverables/submission-20261020-v3/README.md)，旧包保留。仅报告第20页文字变化，前19页渲染一致，其他材料保持字节。记录见[076](taskshot/2026-10-20_076-contributions-update.md)。

2026-10-20 SUB-002按用户要求审查报告与全部提交材料，[修订版入口](deliverables/submission-20261020-v2/README.md)为新的上传依据，上一版保留。报告用`report-reviewed.typ/pdf`新增修订，组员分工原文未改；GUI自检修正残差字段、扫描计数及复制命令，核心方程与物性身份未改。检查范围与过程见[075记录](taskshot/2026-10-20_075-report-and-gui-review.md)。不得把文字清理说成作者身份鉴定或删除必要来源。原生桌面视觉证据仍单独待补。

2026-10-20按用户通知整理第一次大作业四项提交材料，入口为[提交目录说明](deliverables/submission-20261020/README.md)。SUB-001负责新增提交副本、源码重建与发布核验；报告、PPT原件及研究档案保留。GUI-001仍缺原生窗口视觉记录，单独保持未完成，不阻挡已满足教师形式要求的控制台发布版。最终压缩包与逐文件哈希以提交目录manifest为准，未上传课程平台。过程见[074记录](taskshot/2026-10-20_074-course-submission.md)。

2026-10-15用户明确当前需要讲稿、讲解思路、模板具体选页和逐页图文替换指导，由小组组合PPT后再共同优化，不要求代做PPT。展示15分钟、提问另计5分钟，两人分段主讲，姓名与贡献稍后本人填写。制作前审核见[审核清单](docs/preproduction-audit-20261015.md)和[062记录](taskshot/2026-10-15_062-preproduction-audit.md)，本轮整改与指导见[063记录](taskshot/2026-10-15_063-two-speaker-presentation.md)。正文建议13页（[064记录](taskshot/2026-10-15_064-presentation-enrichment.md)新增P5程序实现页，正文改用模板5），A讲1–7、B讲8–13，备答P14–P20，预算13:55含100秒演示，未人工实测。旧阶段包本地缺失，最终定稿后由REL-001重新冻结核验。

## 研究产物

2026-10-16课程报告新初版入口为[Typst报告与说明](deliverables/report_typst_v1/README.md)，PDF在同目录；采用已核实、MIT许可的开源课程报告模板，正文覆盖十项作业要求，六人分工已写入。七张新科研图提供SVG、嵌字体PDF和450 dpi PNG，数据来自保存C结果，明确区分HP主线、历史给定热状态循环与定比热诊断。该目录作为本次报告的图表入口；下文070图集保留为历史整理。模板来源、适配与质量证据见[071记录](taskshot/2026-10-16_071-report-typst-scientific.md)。

2026-10-17 DOC-007已完成教师展示稿校订。最终 PDF 为 `deliverables/report_typst_v1/report-final.pdf`，20页；目录已更新，图例与正文已统一适用范围表述，保留必要模型条件和来源。全文、插图和版面校验见[073记录](taskshot/2026-10-17_073-report-teacher-facing-final.md)。

2026-10-16报告补充动态架构与GUI页面：正文第4.4节插入动态面板24 s静态取帧，第6.4节插入四张稳定GUI截图，并附可播放的冻结HTML。循环截图明确为长十乙一级背景的RP-1富氧补燃研究情景，四个主要数值与C桥接返回核对；GUI只作界面展示，不替代保存C结果。摘要、方法、程序说明、结果和结论同步润色，原输入身份和数值不变。详见[072记录](taskshot/2026-10-16_072-report-gui-architecture-polish.md)。

2026-10-16科研图表集中整理：当前取图目录为`deliverables/科研绘图整理_20261016/01_正文直接插入/`，P6架构、P7/P9曲线和P8/P10/P11原表按当前页码排列；另有8张统一科研风格PNG及SVG/PDF、原始数据/全精度推进剂归档、全部表格Excel、架构备选、历史工况原图和可视化总览。未改PPT或原素材。详见[070记录](taskshot/2026-10-16_070-scientific-figure-collection.md)。

2026-10-16用户明确只改`PPT/终版ppt - 副本.pptx`第7–11页：两张曲线、三张表格PNG和对应标题/结论/页脚已插入并回写，五页渲染视觉检查及包校验通过；其他10页和原母版等包条目逐字节不变。GUI/动态讲解及结尾暂不改。原版备份及验收见[069记录](taskshot/2026-10-16_069-ppt-charts-7-11.md)。

2026-10-16架构与讲稿修订：读取并渲染当前已保存的`PPT/终版ppt.pptx`（15页），未改PPTX。P6改用新增`deliverables/ppt-figures-package/architecture/components-ppt.svg`全宽简图（附2560像素PNG，已视觉检查）；P4保留两条路径，P5保留公式，不使用workflow串行表达。指南和讲稿已同步自然口语、P7–P13替换文字及当前P14参考文献/P15致谢的页码关系。原图约5900行与旧CSV6627行差异未核实，简图和口播不展示行数。详见[068记录](taskshot/2026-10-16_068-architecture-and-script.md)。

图片与操作教程补充：10张官方原图已存[图片备选](deliverables/图片备选/README.md)，其中5张长边≥1600像素、5张1080像素备用；有总览、原图URL、尺寸、哈希和批次边界。两次Grok返回无检索轨迹未采信，实际通过已有官方来源页面HTTP核验并下载。制作指南已逐页补原模板文字到新内容的操作对照，P2大标题为“研究目标”，P3为两张火箭照片＋四级段条目；P4/P6等项目图由用户后续提供。详见[067记录](taskshot/2026-10-16_067-images-and-detailed-ppt-tutorial.md)。

当前最终组装入口已更新为[最终PPT制作指南](deliverables/ppt-making-final.md)，配套defense-script-final.md已同步：P2任务、P3构型、P4路径、P5公式，P7–P11研究页号不变，P12核验、P13四级段结论。主讲仍14页、13:30，备答3页；默认静态图表即可完成。旧ppt-plan-solo.md仅作上一版参考。四张GUI截图已查看，其中cycle-orsc.png实际为开式，不能作补燃图。详情见[066记录](taskshot/2026-10-16_066-final-ppt-making-guide.md)。

2026-10-16用户依据PPT启动脚本选择先做单人方案与讲稿。当前单人制作入口为[逐页方案](deliverables/ppt-plan-solo.md)和[单人讲稿](deliverables/defense-script-final.md)：模板31，封面＋12页正文＋致谢，共14页主讲，另3页备答，预算13:30含100秒GUI演示。搭档只答富氧补燃问题。旧双人文件保留，不再据其页码组装这版。GUI截图及控件操作尚待核验，封面人员与日期、人工计时仍待确认；未生成PPTX。本次按用户“只写文档、不改project/”范围保留任务登记和生成工作面，未流转DOC-004。过程见[065记录](taskshot/2026-10-16_065-solo-presentation-prep.md)。

| 需要理解的内容 | 阅读入口 | 使用边界 |
|---|---|---|
| 两型工作方案、能力和参数缺口 | [四级段研究](docs/two-vehicle-study.md)、[要求映射](docs/requirements-map.md) | 遥一与长十乙首飞一二级分别记录；两型原文截止2026-10-03 |
| 甲烷燃烧与喷管 | [连续液体HP核验](docs/liquid-combustion-validation.md) | C17单相入口表→九气相HP→固定面积冻结喷管；温压为研究假设 |
| 煤油方法 | [固定RP-1入口](docs/kerosene-validation.md)、[边界研究](调研/专题/RES-008_煤油计算边界.md) | C公共API/CLI已有；10 MPa/O-F2.2–4.0指定反应物，国产燃料批次仍未知 |
| 改进计算 | [改进分析](docs/improvement-analysis.md)、[入口响应](docs/adiabatic-inlet-study.md) | 同条件收益、几何代价和输入响应；真实改装量或寿命仍缺证据 |
| 方法比较 | [甲烷/RP-1成对研究](docs/propellant-method-comparison.md) | 同Pc/At/几何/背压，差值由C返回，保留各自入口/O-F身份 |
| 循环 | [循环模型对照](docs/cycle-integration.md)、[新循环核验](docs/engine-cycle-validation.md)、[旧外排核验](docs/cycle-validation.md) | 历史给定热状态模型与新Q=0开式/富氧补燃原型并存；新原型已有本轮统一质量与正式研究归档，泵图谱、真实液相供给、冷却和实机标定仍未闭合 |
| 保存输入、结果与参考 | [研究档案](results/research/README.md) | 每个版本带清单/哈希与失败记录，按其自身日期和构建身份使用 |

[架构三视图](docs/architecture/README.md)说明业务和模块边界。[模型契约](docs/engineering.md)维护物理假设；源码清单由`project/modules.json`维护。

## 复跑

```powershell
python tools/quality.py
python tools/pipeline.py test --configuration Release
./build/release/rocketperf.exe cycle adiabatic cases/vehicles/zq3_y1_stage1.ini --text
./build/release/rocketperf.exe cycle adiabatic cases/vehicles/cz10b_first_stage1.ini --text
./build/release/rocketperf.exe cycle adiabatic cases/vehicles/cz10b_first_stage2_orsc.ini --text
python tools/liquid_combustion.py verify results/validation/liquid_combustion_v1
python tools/kerosene_reference.py verify results/research/kerosene_products_v3_20261006
python tools/kerosene_validation.py verify results/validation/kerosene_anchor_v1
python tools/propellant_comparison.py verify results/research/propellant_comparison_v1
./build/release/rocketperf.exe study propellants --case cases/research/propellant_comparison.ini
python tools/pipeline.py run --model prescribed-cycle --case cases/benchmarks/prescribed_cycle.ini
./build/release/rocketperf.exe interactive
./build/release/rocketperf.exe cases
./build/release/rocketperf.exe study propellants 2.6 2.6 10 0 --text
./build/release/rocketperf.exe nozzle regime cases/research/s3_sealevel_regime.ini --text
./build/release/rocketperf.exe combustion regime-liquid-state coolprop710-cea334-liquid-molar-v1 heos710-cea334-ideal-zero-298.15-v1 liquid 120 1e7 100 1e7 1e7 3.4 40 101325 0.01 --text
```

交互菜单逐项提示单位/默认值（q取消、EOF退出），`--text`输出人读中文表格；二者复用与JSON相同的求解接口，不改变机器契约。`nozzle regime`/`regime-liquid-state`为过膨胀域评估入口：附着求解仍拒绝pa>pe，评估给出理想pe、pa/pe、0.4pa经验分离参考（提示非预测）、匹配/分离参考面积比。

研究归档复核使用已保存文件；重新生成参考需要固定上游构建或可选物性环境，要求见相应工具说明。正式运行使用manifest指向的新鲜已测试构建。`build/release/rocketperf.exe`是便捷别名；新RunId/研究版本不能覆盖旧记录。

## 必须解释的限制

- RP-1、NIST surrogate和国产煤油批次是不同输入身份；四对象映射关联证据和方法，尚不足以构成真实性能卡。
- 推力室、整机、整箭口径分别使用。单喷管HP不闭合支路轴功、回流、喷注或泵后过程。
- 新循环输出的开式/补燃架构是研究情景；朱雀三号家族证据、长十乙一级家族证据和长十乙二级待判状态不能改写成具体首飞子型性能。
- 新循环本轮已完成统一质量和正式研究归档；`build/engine-cycle-second-probe`仍是早期开发试跑，不是冻结交付。推荐复核`results/research/engine_cycles_v2_20261013/manifest.json`及其验证命令。
- 约302 s和约193.65 MW来自给定热状态合成循环；后者是模型所需排热，不能直接当作冷却设计负荷。
- 面积和背压研究不计算质量、侧载、流动分离或寿命。局部扰动是情景响应，不能称概率置信区间。
- 域评估的0.4pa是Summerfield型经验分离参考：pa>pe证明理想pe低于背压，不证明实际分离位置；匹配/分离面积比是理想公式反解，非设计建议。
- CEA/Cantera等同源数据对照验证软件方法；机械PASS不构成独立实验或具名科学审查。
- 日常构建与交付使用Windows。历史WSL sanitizer结果只覆盖当时版本；远端CI配置不等于执行记录。

公开字段缺失时继续独立方法研究，并记录其影响。具体任务顺序以worknow为准。[报告](deliverables/report.md)、[逐页制作指导](deliverables/ppt-structure.md)与[讲解思路](deliverables/presentation.md)已衔接。小组组合PPT后再优化；组号、姓名、真实贡献、人工演练与最终四件套验收仍待完成。

组员参数审阅见[RES-009](调研/专题/RES-009_组员参数审阅.md)：产品参数与试验产品保留各自身份，TQ-15B能力误归属和长十乙后缀推断不能进入输入。最终Windows计算程序直接由C运行，辅助工具单列于开发/参考附件。

## 交给其他组员

本地阶段交付的源码包、运行包与详细解读见[交付说明](docs/delivery.md)和[项目解读](docs/project-guide.md)。当前不执行远端同步或Release；如需外部发布，必须由用户另行明确授权。压缩包固定一个干净提交，源码重建和exe运行记录随交付保留。

按[接收说明](docs/receiving.md)固定干净提交后生成运行包与离线源码bundle，接收者实际复跑成功与拒绝案例，并说明确认与未确认内容。新包v3使用`checks`记录接收检查，v2保留任务快照，v1/v2可读；旧包只代表其固定版本。

近期批次：[答辩讲稿立体化与演示页语法修复](taskshot/2026-10-15_061-defense-narrative-and-demo-syntax-fix.md)、[演示页重构、HP提速与工程证据](taskshot/2026-10-15_060-demo-rebuild-and-hp-speedup.md)、[凝聚碳判据与代码规整](taskshot/2026-10-14_059-carbon-guard-and-tidy.md)、[答辩前代码与叙事审查及演示页](taskshot/2026-10-14_058-defense-review-and-demo.md)、[代码质量实质改进与真实核查](taskshot/2026-10-14_055-quality-substance-and-reality-check.md)、[答辩内容核查](taskshot/2026-10-14_056-defense-content-integrity-check.md)、[文档群与目录整理](taskshot/2026-10-14_057-repo-tidy.md)、[汇报前质量整改](taskshot/2026-10-12_049-quality-readiness.md)、[参数审阅与RP-1接口](taskshot/2026-10-06_042-parameters-and-rp1.md)、[RP-1研究](taskshot/2026-10-06_040-kerosene.md)、[维护整顿](taskshot/2026-10-06_041-maintenance.md)。历史过程见taskshot；风险与补审见[review](docs/review.md)。每个实质批次审查并本地提交；外部推送需另有授权。

本轮文档入口和新旧循环口径整理见[2026-10-13整理记录](taskshot/2026-10-13_051-document-map.md)；完整阅读导航见[文档索引](docs/README.md)。

## 收尾总览与组员代码接收

2026-10-18课程报告与答辩终稿入口见[最终交付清单](deliverables/FINAL-DELIVERY.md)：20页报告 PDF 与 Typst 源码、17页答辩 PPTX、C17源码/Windows运行包以及 GUI 便携包。交付清单同时列明复现命令、SHA256、研究输入边界与 GUI/C 体系后续工作。当前统一质量入口已在主工作区完成一次六组 PASS；GUI 浏览器预览和桥接测试通过，原生窗口视觉截图仍待单独留证。最终包生成后应以其 manifest 与校验文件记录的固定源码提交为准。

2026-10-13的 `代码.zip`已按字节保存于[接收原件](调研/原始来源/20261013_classmate_code/)，交接与两份 `model-data`分别有哈希身份。实际启动、源码重建、模型差别和参数线索见[代码包审阅](docs/incoming-code-review.md)，研究/展示/最终交付缺口集中在[收尾总览](docs/final-overview.md)。同学的给定温度补燃模型与甲烷代理YF算例没有覆盖当前绝热求解器，也没有更新型号事实截止日期。

无参数闪退来自同学旧命令行exe的退出码2；其bat正常交互可用。当前交付工具v3收齐菜单8的五个研究情景，并提供定位包目录后调用C菜单的 `rocketperf-run.bat`；源码和运行包分别复核17项演示。使用前核验对应本地包manifest为PASS，不把原包中绑定旧exe的测试报告当新exe证据。最终报告、PPT、真实贡献及演练仍按任务契约完成。答辩演示页`deliverables/demo/index.html`为离线单文件（六页），由`tools/demo_data.py`用已测Release exe生成数据并从`deliverables/demo/src`组装；只改页面源码用`--assemble`，改C或输入后重跑并`--check`。九气相平衡在收敛后计算石墨活度，`a_C>1`返回越域（凝聚碳区）；石墨拟合在`src/thermo/graphite_generated.h`，固定气相数据集不变。

报告技术审稿已补齐第7.6节的循环输入、质量/轴功/热量关系及结果；[现行流程图](docs/architecture/report-flow.svg)区分独立入口。朱雀三号二级与长十乙二级开式使用相同数值输入，不算两份独立物理验证。交付verify改读包内INI，检查全部成对输入/差值，并逐个比对菜单显示与JSON；v1/v2/v3已检查旧包兼容。源码未扩展模型适用域，具体问题见[补审记录](docs/review.md)。
