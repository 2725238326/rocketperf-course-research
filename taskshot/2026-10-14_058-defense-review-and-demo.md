# 2026-10-14_058：答辩前代码与叙事审查及交互演示页

- 关联任务：QA-005
- 本轮请求/范围：用户确认答辩15分钟、PPT小组自制；要求审核代码问题、核对讲述内容与创新点、做清晰的前端演示页，当晚保证大部分内容无问题。
- 起始状态：HEAD 99b96d1，52/54 DONE，DOC-001 BLOCKED。

## 实际检查和改动

- C核心逐模块审读并实测CLI边界输入；发现与处理逐项见[review](../docs/review.md)“答辩前代码与叙事审查”节。
- 叙事物理错误：推力差被归因于c*。固定Pc/At时`F=CF·Pc·At`，c*只决定流量。改[报告](../deliverables/report.md)7.2/7.5/判断1、[成对研究](../docs/propellant-method-comparison.md)；数字均未变。
- 讲稿[presentation.md](../deliverables/presentation.md)按15分钟重排为11页：新增P3工作点页、P5/P7现场演示、时间预算、演示操作清单与Q&A补充；[收尾总览](../docs/final-overview.md)记录时长变更。DOC-001验收条款仍写10分钟，未改契约，待用户在解除阻塞时修订。
- 演示页[demo/index.html](../deliverables/demo/index.html)：推进剂取舍、面积比与背压、循环三本账三页；数据由[demo_data.py](../tools/demo_data.py)调用已测Release exe生成。
- 源码注释：adiabatic.c/frozen.c/ideal.c/equilibrium.c头注释与代码判据不符处改正，代码逻辑未改。

## 验证结果

- `python tools/demo_data.py`：2213次C运行，504点被C拒算（全部为过膨胀out_of_domain）；`--check`逐字段复现。
- 浏览器1920×1080实测三页：无滚动、无控制台错误；页1默认读数324.43/310.57 s与归档一致；页3质量/轴功/焓残差与报告7.6一致（−0.896 W / 0.827 W）。
- 统一质量入口结果见QA-005验收证据。

## 未解决和下一步

- 甲烷连续液体方法是否把O/F域收窄到避开富燃凝聚区，需用户决定（会牵动C接口、测试和交付verify）。
- PPT实物、组员确认贡献、实际计时演练仍由小组完成；PPT定稿后重跑quality绑定最终版本。
- 讲稿未实测计时。

## 交接更新

任务板经工具登记QA-005；handoff近期批次已加入本记录。
