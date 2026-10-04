# 入口边界与作业架构：提交后复验

日期：2026-10-04。接续[本轮计算与图形快照](2026-10-04_026-thermal-boundary-and-assignment.md)。此记录是本机软件复验，不是另一位组员的接收或独立科学审查。

## 固定提交

`41ef344dc38ccfcc7cd475cee956576b402eabee`固定七组C入口焓/密度运行、热边界结论、作业对接SVG/离线四视图、反例测试与ANA-005验收。提交前暂存区检查和Git hook通过；提交后主工作树干净，没有推送。

三条作业研究主线、源码/发布版/PPT/报告四项交付及未覆盖范围分别标明。四张SVG在本机用Sharp重新渲染并视觉核对，预览在`build/architecture-review-ana005/`；不含外部图片、字体请求或CDN。当前首图为`docs/architecture/assignment.svg`。

## 独立源码检出

确认`build/clean-ana002`工作树干净后，从本地origin快进到41ef344，独立运行`python tools/quality.py`。没有复制主目录build或exe。结果6/6 PASS，质量指纹与主目录相同：

`3a88fa5cab73e3990f13079e39c9bfe59e59ef130697eb9cdd2894d3d7c3008c`

Debug/Release各4308项C检查、CLI27组；参数8、物性5、CEA15、循环参考13组；治理20、runner25、交接6组，零跳过。独立报告为`build/clean-ana002/build/quality/latest.json`，SHA256为`a19422489e0e267af88ff13af912b906deb1183fe02eaac10333c55347e95561`。

## 本地阶段交接包

`build/handoff-41ef344`固定上述提交；create、verify及actor=root/maintenance的本机receive均PASS。隔离PATH的包内成功案例退出0、预期越域案例退出4；只有Windows系统DLL依赖，源码以离线bundle交接，不依赖远端。

- 包清单SHA256：`1d8ff56f65f44505aee75f198bb8f17af091ae2e18e61e1460861bb692656154`。
- source.bundle SHA256：`8addfcae996c590e32e138156a7b355305b9d1e08f6488bd1993cea14edcca7f`。
- 本机收据：`build/handoff-41ef344-self-check.json`，SHA256为`13ef4c7b87517d395b2588b4909285f8093ba5f7b7a88784337c37dd720c5fd4`。

旧交接包、构建、参考和原始来源没有改写或删除。包不包含随后新增的本收据快照，仍固定41ef344。实际接收者按[接收说明](../docs/receiving.md)具名复跑并说明维护职责；本机收据不能代填真实组员贡献。

## 接续

ANA-006已解锁：同NASA9基准的显式入口焓HP与固定喉面积方法验证。液态温压/焓基准、煤油、全循环硬件/压损/热闭合、冷却和整机独立参考仍缺。DOC-001依赖ANA-006，PPT与最终报告继续后置。任务状态以生成工作面为准。
