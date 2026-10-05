# 固定液态锚点版本的源码与交接复验

日期：2026-10-05。固定提交`5a7546f40266f46bc1d66e34c3d798257aaa9b5d`，保留原运行的HEAD、dirty和构建身份，不回写历史。

- 独立源码克隆`build/clean-ana008-5a7546f`完整质量6/6 PASS；与主工作区同指纹`5fcd215a4d0086d862a62f504f152b96b22788e1a4611cfaa5730f54fbf6e240`。
- 克隆质量报告SHA256：`e367c58271bbbee96e0841ebe456042952c4d4e5d260e964b77aac683db88c36`。不依赖主工作区的旧exe，也不要求CEA/Fortran运行环境才能复核已保存参考。
- 正式v1包`build/handoff-5a7546f`包含已测Windows exe和离线source.bundle；包校验及成功循环/预期域拒绝复跑通过，`test_fixture=false`。
- 包清单SHA256：`2cac74ccfeb220eee27565358906a8386c1b43f4843eb13b5c6c84aac8179e4f`；接收记录`build/receipts/ana008-root.json`由root以maintenance角色生成。

这是同机同agent的软件复验，不是独立人员验收或科学验证。

复跑还发现交接工具按登记顺序把DOC-001放入`next_task`，与该提交worknow明确指定RES-007不一致。该包计算能力和哈希复验通过，但接续推荐有缺陷；维护以源码worknow为准，PPT后置。旧包保留不改，GOV-002修正选择逻辑并另建新包，见[修正快照](2026-10-05_034-handoff-routing.md)。
