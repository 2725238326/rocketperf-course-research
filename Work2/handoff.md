# 作业二交接

从[worknow](worknow.md)读取当前任务；在仓库根执行 `python tools/project.py doctor`，再 `show TASK-ID`。任务状态、负责人、依赖和验收以登记为准，本文件不维护第二套状态表。

## 2026-10-24首轮调查

[调查协议](research/survey-protocol.md)覆盖方法/验证/C引擎/AI/参数五条主线。[调研入口](research/README.md)连接实际原文、分级主张、软件版本/许可、参数观察和缺口；精选JSON由根`tools/work2_survey_data.py`生成，原件由`tools/work2_research.py verify`及统一质量复核。

Grok已持久修复重复/v1路径，增加无检索轨迹拒绝与脱敏失败记录。本批一次请求无轨迹、另两次有17/10条结构化调用记录；不是接口始终可用的保证，也不替代原文核验。参数新观察是英文TQ-12A产品栏面积比20.5，仍未得到同批完整输入。旧arXiv:1805.07762化学平衡引用已被原站否证，旧返回保留不采信。

课程与现用物性文件完整字节不同，但选定10种气体字段一致；[方法调查](research/method-review.md)解释同源数据边界。[C引擎](research/c-engine-review.md)先建议补workspace/失败/累计诊断，[AI调查](research/ai-review.md)把已有ODML与2026二元LLE工作分开，未承诺新算法或GPU收益。2020 Springer原文仍受挑战页限制。

本批没有新TP/HP运行、训练集或GPU任务。下一步优先WBASE固定基线和参考、补累计工作量与误差审查，再由WREF冻结数值阈值和数据协议。不要把19条调查主张、43条参数/缺口观察或下载量当计算结果。过程与验收见[002执行记录](taskshot/2026-10-24_002-research-campaign.md)。

## 2026-10-23启动批次

已完整阅读633行[启动词](提示词/start0.md)及两张图片。实际原始资料为9份、21,284,631字节，其中课程PDF为54页和50页，NASA手册为58页和184页；完成文本抽取及相关页初读，未声称逐页精读全部手册。文件身份见[原件清单](project/sources-20261023.json)。

活动文档放Work2，根目录保留共享C工程、任务/模块登记和质量工具。[作业一归档导航](archive/work1/README.md)采用原址保留，新增[固定交付核验快照](archive/work1/baseline-20261023.json)：162项材料、ZIP SHA256/大小/CRC和对应包内字节核对。原包未重写。用户已有的另一个解压目录不并入本轮提交。

教师要求已逐条映射到[requirements](docs/requirements.md)。展示10分钟、提问5分钟；“12月5日（周五）”与2026日历不符，按[U-001](docs/review.md)保留待核。不得沿用旧15分钟讲稿。

Illinois在源码中已确认为HP外层假位法，化学平衡内层是Gibbs/元素势阻尼Newton；继承范围和复核要求见[baseline-audit](docs/baseline-audit.md)。此处没有声称本轮完成新的物理模型验证或性能突破。

指定Grok已DryRun并实际请求，返回HTTP403，见[失败记录](research/search/20261023_w2_methods_a.failed.json)。没有取得可采信的本轮在线文献，不用浏览器补搜。本地初读与研究问题见[首轮笔记](research/notes/2026-10-23-first-reading.md)和[来源台账](research/evidence.md)。历史型号证据截止不变。

本批操作、检验及限制见[执行快照001](taskshot/2026-10-23_001-bootstrap.md)。正式验收依据通过任务工具保存于根project/evidence，不能把文档建成视为科学结论验收。

## 接续方法

按生成工作面顺序领取。基线审查与权威方法/评价基准调研可以分别准备，仍顺序执行；接口问题仅影响新在线核验，不妨碍公式推导、已有测试及验证协议准备。先预注册适用域、指标和比较条件，再决定是否引入AI或大量算力。

作业一尚缺GUI原生视觉、具名接收/人工演练等证据，原负责人和旧任务保持原样。其进一步补验范围留待用户后续规划，不用作业二启动暗中改写作业一完成声明。
