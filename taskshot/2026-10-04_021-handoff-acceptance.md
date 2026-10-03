# 阶段交接复验

日期：2026-10-04（北京时间）。接续[QA-001修复记录](2026-10-04_020-quality-and-handoff.md)。本记录只记实际工程验收，不新增研究结论。

## 验收结果

主工作区完整质量通过6/6，质量指纹为`20ae51fc8d09d23eb3024d9e74f7938ae0e49ae815f2b1bc866b027299613843`。Debug/Release分别运行core207、adapters29、thermo1175、combustion2512、cycle241项和CLI22组，零跳过；参数数据8组、物性数据5组、CEA参考3组、循环参考6组。治理18组、运行管理19组、交接6组通过。CMake/Ninja另通过6/6 CTest。

修复提交`acc6ff1`后生成正式模式运行包`build/audit-20261004/handoff-review/`，verify及具名本机receive通过；成功退出0，越域拒绝退出4。该记录是本机预验，不是其他同学或独立科学审查。

## 独立检出暴露的问题

从运行包source.bundle新克隆后，主/克隆指纹不一致。逐文件定位到`data/thermo/fixture_nasa9.tsv`：现有工作树最后一行CRLF，但旧Git blob为LF；新增-text规则尚不能自动重新固定已跟踪文件。

用`git add --renormalize`将夹具现有字节明确入库，未编辑其物理数值或原始来源；提交`cca01de`。没有把原始资料的哈希改成忽略行尾，也没有覆盖旧v1验证归档。修正后重新生成包并独立克隆到`build/audit-20261004/clean-source-normalized/`，主/克隆指纹完全相同。独立克隆重新执行全部6组质量入口，结果PASS；报告位于该克隆的`build/quality/latest.json`。

曾在局部回归后过早将任务标DONE，随后重开并记录原因；正式包与独立检出验完后才完成最终验收，事件历史保留。另一次额外生成的重复循环归档移到`build/audit-20261004/duplicate-cycle-v2-check/`，没有删除它或当作正式研究证据。

## 对外接手边界

最终包在结项提交后重新生成，版本由包内handoff-manifest的project_head决定，不拿旧包的HEAD冒充最终提交。包、ZIP、本机接收记录及独立检出证据均位于build，不进入源码仓库；下次修改代码必须重新质量验收和打包。

接手者按[接收流程](../docs/receiving.md)在自己的Windows机器执行verify、成功/失败演示和具名receive，研究负责人另确认事实、假设、口径与不可外推结论。当前仍是给定热状态合成循环；两型真实参数与改进研究继续ANA-002，最终PPT/报告后置。没有推送或公开上传。
