# 文档与仓库维护审计

审阅日期：2026-10-12。范围为现行项目入口、研究规划、工具说明和交接协议。原始资料、历史taskshot与既有参考不重写。

| 问题 | 处理 | 维护位置 |
|---|---|---|
| 交接末尾重复追加历史批次和旧命令 | 按研究产物、复跑、限制、接收重排；历史详情链接taskshot | handoff.md |
| 现行规划含过期的第一批动作和旧模块计划 | 以课程三条研究路径、产物与进入条件组织；Git保存旧稿 | docs/project-plan.md |
| 研究索引仍写首轮日期，缺少专题入口 | 明确首轮和各专题日期；补液体/RP-1与工程审查入口 | 调研/README.md、调研/专题/README.md |
| 交接名称不能说明检查目的 | 新包v3使用checks；保留旧字段读取兼容；拒绝错版本/双字段 | tools/handoff.py、tests/test_handoff.py |
| 煤油计算只有计划 | 固定RP-1研究驱动、15张CEA卡、失败边界及方法契约 | RES-008专题与results/research |
| 生成式审阅被当成结论保证 | 核验NIST/GitHub正文，维护来源/复现/语义审查规则 | docs/research-writing.md |
| NIST正式risk-management网址触发密钥误报 | 加入凭据标记边界；真实Bearer/带引号凭据和网址分别测试 | tools/project.py、tests/test_governance.py |

README导航；worknow/任务板展示登记状态；rules维护约束；handoff维护接手路径；专题回答研究问题；taskshot保存执行事实。实时Git状态用doctor，任务事实通过project.py修改，说明中不维护第二套状态表。

本批次没有改变生产模块依赖，架构SVG沿用与登记一致的版本；研究驱动放在tools，公开生产燃料接口尚待验证。中间RP-1纯CEA/失败试跑移至build，正式v3档案进Git；源码、输入、日志和哈希可追溯。新下载原文用日期身份，原始索引只追加。

写作审阅删除无依据评价、催促式语句、重复工具自述和失效动作。公式、单位、失败原因和限制保留。历史术语保持当时原样，旧持久化字段只在兼容代码/测试中使用。依据见[写作规则](research-writing.md)和[原文核验](../调研/专题/工程内容审查_20261006.md)。

先运行完整质量检查，再审查暂存区并提交已审阅文件；版本和检查记录见[执行快照](../taskshot/2026-10-06_041-maintenance.md)。

## 2026-10-12 汇报前质量整改

QA-002 针对当前代码、研究表述和交付基础做了集中复核。已修正 `gamma→1` 面积反解的数值消去、冻结喷管重复物性计算、非法背压与诊断字段的失败保持、交互超长输入和浮点转菜单索引；新增液态过膨胀交互回归。新增 `tools/static_analysis.py` 对登记的28个生产C源文件执行 GCC 14.2.0 `-fanalyzer` 与严格警告，新增 `tools/benchmark_frozen.py` 保存固定旧版/新版交替采样和推力校验。

本轮交付脚本补齐菜单列出的6个算例、域评估文本、中文交互和网格扫描；当前交付协议为v2，`tools/delivery.py` 仍读取旧内部包协议，14项交接测试通过。当前性能记录为单机固定2000次A10/A40冻结喷管求解，中位CPU时间旧版0.159 s、新版0.085 s，累计推力校验值均为360319492.45191073 N；该记录只说明本机该输入的实现开销，不是发动机精度或通用加速保证。证据目录和最终阶段包路径写入QA-002快照。

## 2026-10-13 文档群与循环状态对齐

新增`docs/README.md`按接手、研究、模型、验证和交付分层导航；根`README.md`缩短为项目概述、当前循环入口和常用命令。`docs/engineering.md`、`model-design.md`、`two-vehicle-study.md`、`project-guide.md`、`technology-stack.md`和架构图同步区分历史`prescribed_thermal_cycle_v1`与新增`adiabatic_single_shaft_cycle_v1`；后者仍是MOD-009中的条件性原型，未把家族资料写成飞行子型性能。

新增[循环集成对照](cycle-integration.md)、[新模型验证页](engine-cycle-validation.md)和`vehicle_cycle_evidence.json`；原循环验证页仍保留其v1契约，并链接新版本。数据图只登记来源身份/未知字段，不成为求解输入。调研索引说明2026-10-12两次循环检索返回没有实际搜索轨迹，故其内容不能作证；五份本地原文复读与既有文件哈希一致，没有刷新型号参数。

`python tools/project.py check`通过（550个本地链接、无问题）；四张架构图重新生成，更新的作业图和组件图已渲染目视检查，无裁切/重叠；新增循环证据JSON校验通过，开发档案复核为5个成功案例、4个预期拒绝、12张CEA卡、814条状态关系。MOD-009仍ACTIVE：本批文档整理不替代代码/文档变化后的统一`quality.py`、新鲜Release、静态分析和正式受版本控制的研究归档。
