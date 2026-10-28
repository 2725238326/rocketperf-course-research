# 作业二交接

从[worknow](worknow.md)读取当前任务；在仓库根执行 `python tools/project.py doctor`，再 `show TASK-ID`。任务状态、负责人、依赖和验收以登记为准，本文件不维护第二套状态表。

## 2026-10-28基线与前沿

[基线审查](research/baseline-validation-v1.md)与[选定清单](results/baseline_v1/selection-manifest.json)固定源码/数据、四类身份、事前协议及失败记录：84项主矩阵（67成功/17正确拒绝）、54同源物性独立实现比较状态、13层级参考及3CLI拒绝均按门槛通过。生产src/include未改；研究侧计数与原始输出逐例一致，中心HP累计201步而末次字段仅1步。全链物性/失败API、暖失败冷回退、Jacobian/初值条件性仍有差距，不能据矩阵声称实机精度。

两份独立新Debug共60次循环进程各505项零失败，U-015仍未定位。原异常构建已由WGOV清单删除，不能精确复跑；原报告/哈希/当时复跑记录已复制进选定档案。后续清理必须保留未决异常构建ID/裸哈希，不能以这批通过关闭原因问题。

用户再次强调前沿获取。[本批核读](research/frontier-review-20261028.md)含FastChem4（2026）、CT原稿/2026期刊元数据、JCP2025作者全文选定页；Grok一次502、一次7条工具轨迹，HTTP核读纠正摘要的物种/跨体系HP适用性错误。来源主索引75条、67可核字节，首轮成员不变。后续路线冻结前继续有截止的定向查新；新不等于适用，先传统强对照和总成本小实验。

本批执行与实际质量补记见[006记录](taskshot/2026-10-28_006-baseline-frontier.md)。submit和commit前按本轮用户要求分别确认；在确认前不流转REVIEW/DONE或创建提交。之后WREF另冻结正式保留集，本批已接触点不能当未探测测试集；WRES-002全文/软件版本/同批输入缺口继续按契约承接。

用户随后已确认WBASE验收；暂存预检补齐baseline_v1的Git字节保留规则和真实clean过滤回归，完整质量与任务流转的最后事实见006补记/任务登记。commit仍需单独确认；不把原第一轮质量当修正规则后的新鲜证据。

## 2026-10-28清理盘点

WGOV-001（devin）完成未引用构建产物清理：删除73项（58个未引用artifacts构建+15个作业一scratch目录），释放约1.43 GB；引用扫描覆盖5339份文本并留证于[manifest](results/cleanup_v1/manifest.json)。`.cmake`/`CMakeFiles`/`Testing`删后被构建与IDE重新生成，保留为工具副产物。Debug/Release重建测试与统一质量六组PASS，详见[005记录](taskshot/2026-10-28_005-build-cleanup.md)。[用户材料证据清单](results/cleanup_v1/user-materials-evidence.md)仅列事实：四份交付zip版本互异、PPT/PPT/嵌套约549 MB，删除决定权留用户。本批不涉科学验证；WBASE-001仍为下一棒，含U-015补核。

## 2026-10-24两型深化

[两型专题](research/vehicles/README.md)按[十维方案](research/vehicles/survey-plan.md)组织朱雀三号、长十乙与[同口径比较](research/vehicles/comparison.md)。新增VTVL两次试验、B型地面考核和海上回收/原始采访核读；历史原件原址复用，获取日期保留。事件、产品和家族证据不升级为同批性能卡，未支持的YF-219型号/台数仅留线索。

source-index累积，首轮46条成员保持；两型精选由`tools/work2_vehicle_data.py`生成，逐条查短引文、来源核读/可用性及未知值，覆盖表不给全网完整率。箱头起动论文只有元数据，130吨级论文只有摘要；主室/入口/冷却/精确装机/寿命仍有缺口，见U-016/017。没有新增生产算例、科学TP/HP数据或GPU实验。实际批次和质量见[004记录](taskshot/2026-10-24_004-vehicle-dossiers.md)。

## 2026-10-24业务架构

[业务架构](docs/business-architecture.md)和[业务图](docs/business-architecture.svg)明确五项职责：对象/证据、场景/模型、C计算、实验/评估、结论/交付。场景、物理模型、数值策略、执行配置分别保留身份；型号名关联背景证据，计算接受完整输入。求解状态、结果评估和目标适用性分别说明，失败与参考分歧进入研究记录。

该批是目标设计和后续任务契约收敛，没有改生产C模块或生成新的科学基准/AI收益证据。共享工程图继续描述当前登记，新增Work2图经同一生成入口检查漂移。WBASE/WREF/WDEV承接实际契约与实现；细到科学主张的自动失效传播仍是目标。设计走查与验证范围见[003执行记录](taskshot/2026-10-24_003-business-architecture.md)。

质量检查出现一次Debug循环测试0xC0000005，随后同一二进制单次及固定10次均通过505项检查，原因未定位；[U-015](docs/review.md)保留给WBASE补核，不把后续通过说成已修复。

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
