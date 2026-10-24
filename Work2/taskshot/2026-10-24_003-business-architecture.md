# 003 · 作业二业务架构与领域契约

日期2026-10-24，任务WARC-001。用户要求重点设计业务架构，承接前两轮研究规划与质量指标讨论。起始分支codex/work2、HEAD 7a3632e；唯一已有未跟踪内容是deliverables下第一次大作业解压目录，保持原样且不纳入本批。

## 执行范围

核对Work2入口/规则/交接、需求与研究协议、现有模块登记及公共C契约，运行doctor确认无活动任务后通过根工具新增并领取WARC-001。以五项业务能力连接证据、场景、C计算、实验评估和结论交付，定义概念对象、用例、比较类型、状态维度、当前能力差距和分阶段演进。

新增业务架构正文与可生成SVG/Mermaid，接入统一架构生成/漂移检查、规范归属和阅读导航。后续WBASE/WREF/WDEV契约通过工具补充职责边界，继续使用唯一任务事实源。未修改生产C模块或原始资料，未做新外部检索、新TP/HP实验、训练或GPU运行。

TQ-12A产品参数与HP预测实验用于设计走查；前者检查批次/输入缺口，后者检查同模型比较/回退/成本，不代表实算结果。目标设计、当前实现、机械质量和科学结论分开标明。

## 验证与交接

统一架构入口已生成五份SVG、五份Mermaid及原有工程离线HTML。项目检查通过77项任务登记、1121条本地链接、96项既有来源、9份启动原件和40份调查字节身份；无生产模块登记变化。

临时预览位于build/work2/architecture。PyMuPDF预览用于初读；直接SVG浏览器截图等待超时，改为本地HTML内嵌SVG后成功。1600×1050最终预览实际检查了文字、箭头、虚线及边界，修正C诊断连线穿过说明文字的问题。首次质量尝试在图形修订前主动中止，最终验收只认修订后完整运行报告。

接续以生成工作面为准，不在本文复制实时任务状态。

修订后第一次完整质量尝试于北京时间09:33:36–09:34:17在Debug组失败：构建85a23407c5174bc8b7e53e2ba7f6f8fa的test_cycle.exe返回3221225477（0xC0000005），cycle-test.log为空；project/governance已通过。原失败报告复制到build/work2/architecture/failed-quality-20261024.json。该二进制SHA256为d2bea05d71bde9f5b4398cf667ac96ed2bcb11cab3b1b4e7b31d05b2720c84dc。

使用pipeline相同subprocess_env对同一二进制顺序复跑：首次退出0、505项零失败；事先固定再跑10次，全部退出0且各505项零失败。原输出保存在build/work2/architecture/cycle-crash-probe.json与cycle-repeat-probes.json。没有因复跑成功而宣称根因已修复；U-015交WBASE继续审查，保留失败和成功两类事实。没有改C代码、降低检查或屏蔽失败。

最终`python tools/quality.py`于北京时间09:38:00–09:45:45运行，project/governance/debug/release/runner/handoff六组PASS，Release包含GUI构建与测试；输入指纹f5375af652e379a1468194dabe9c791e88df4dd48e66840dfce05291d171a900。WARC-001经ACTIVE→REVIEW→DONE，验收快照见[WARC证据](../../project/evidence/WARC-001_15e1b066d935.json)。WBASE自动解锁承接实算审查，U-015仍未关闭。

该通过记录覆盖本批文档/工具一致性及既有程序检查，不构成新方法收益、实机精度或独立科学审查。后续按生成工作面推进；最终暂存区核验与本地检查点以本批Git记录为据，不推送或发布。

最终审查21项本批文件，`project.py check --staged`与`git diff --cached --check`均PASS，无未暂存的受控文件变化；未纳入用户已有解压目录。按规则建立本地检查点，提交身份以Git记录为准。
