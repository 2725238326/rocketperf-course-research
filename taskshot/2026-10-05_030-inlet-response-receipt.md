# 固定入口响应版本的源码与接收复验

日期：2026-10-05。固定提交`a5852b3d23852a96132d42429cc0bff1409a4d09`，不回写旧运行的HEAD或dirty字段。

## 已有复验

- 独立干净源码克隆：`build/clean-ana007-a5852b3`，完整质量6/6 PASS。
- 主工作区与克隆输入指纹相同：`a2c450b07cd69075d3b3ea601206f7b0ee9ce915a53ae847ba5727773756da07`。
- 克隆质量报告：`build/clean-ana007-a5852b3/build/quality/latest.json`；SHA256为`2b368cd6c18b5e577644d3ba4877c8d7b5aa2d7ac954a205f894c0b95c6a95cb`。
- 从干净提交生成正式包`build/handoff-a5852b3`，包含已测exe与离线`source.bundle`，`test_fixture=false`。
- 包清单SHA256：`b2341102f355b1cb78b995ac4c62b4a369e5e7a1d58cc758f48753de22c30c1d`。
- 接收记录`build/receipts/ana007-root.json`：actor=root，maintenance；成功循环退出0，预期域拒绝退出4。另运行包内hp-h成功，液态入口退出4。

这是同一机器、同一agent的软件复验，不是独立人员验收或科学验证。包固定该提交，不自动包含后续研究。此快照按前轮已生成文件核对，不把新研究的质量状态写进旧包。

## 接续

RES-006核验液态甲烷/液氧与煤油入口的温压、相态、焓基准、密度及C17路线。PPT/报告仍后置；不推送远端。
