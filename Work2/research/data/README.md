# 调研数据与批次范围

原文下载与调查数据分别保存，以下JSON是可复核的结构化记录，不是发动机性能卡或AI训练集。

| 文件 | 用途 |
|---|---|
| [source-index.json](source-index.json) | URL/最终URL、获取时间、HTTP/可得性、路径、SHA256/大小、发现途径与实际核读范围；保留失败 |
| [claims.json](claims.json) | 已核事实、派生、假设及来源/定位/局限；生成回答不直接升级为事实 |
| [software-catalog.json](software-catalog.json) | 固定版本、核心语言、许可、C接口区别与本批使用范围 |
| [parameter-observations.json](parameter-observations.json) | 子型/批次/工况/原单位与参数/未知观察；未知值为null |
| [thermo-comparison.json](thermo-comparison.json) | 两份原始数据库的选定10种气体字段对比，非整库等价或独立物性验证 |
| [coverage.json](coverage.json) | 实际覆盖、数量、未解决问题与零新求解/训练/GPU运行事实 |
| [vehicle-evidence-v1.json](vehicle-evidence-v1.json) | 两型深化的版本/参数/事件观察、冲突、论文可得层次及未支持线索；不是生产算例 |
| [vehicle-coverage-v1.json](vehicle-coverage-v1.json) | 两型十维问题的已查子集、剩余缺口、独立批次成员与数量 |
| [frontier-20261028-v1.json](frontier-20261028-v1.json) | 定向新方法、原文范围、摘要纠错和待验证候选，固定本批7条来源身份 |

原件位于上级raw日期目录，失败记录保留在索引；HTTP200也可能只是挑战页（W2-A03），可保存但不能支持科学结论。两个本地既有物性来源按原路径复用，没有复制或改写。

`tools/work2_survey_data.py`维护本批精选结构化条目并生成claims/software/parameters/coverage及物性对比；用 `python tools/work2_survey_data.py --check`核对漂移。`python tools/work2_research.py verify`和根统一质量检查原文哈希、来源引用、未知数值及精选数据一致性。更新精选字段须改生成源并再生，不只手改JSON。

source-index是累积主索引；首轮coverage的成员固定为最初46条，新采集不能倒记为首轮已完成。两型深化由`tools/work2_vehicle_data.py`维护独立精选和29条选定来源范围，用`--check`核对生成漂移、引文、未知数值和来源核读状态。两份coverage的分母不同，不能相加当独立论文数或完整性比例。

获取新原文用 `python tools/work2_research.py fetch W2-IDNN URL --kind html`（按实际类型选择），唯一ID、原文不可覆盖，索引原子更新。研究状态“已保存”“已读相关节”“数值复现”“物理验证”保持区别，实际读过的范围才写入read_scope。

新日期批次显式加`--archive-date YYYYMMDD`，兼容默认仍为首轮20261024，不将新获取静默归入旧批次。前沿精选由`python tools/work2_frontier_data.py`登记并生成，用`--check`验漂移。统一research verify同时核选定基线：哈希/标签以外重算守恒/反应亲和、参考差异、累计计数关系和原始输出对应。

旧档原址复用用`python tools/work2_research.py reuse W2-VLNN OLD-SOURCE-ID`，先检查旧索引的字节身份；保留原saved_at作为retrieved_at，新registered_at只记录本阶段登记。复用不复制原文，也不刷新在线日期；下载/复用后均先为downloaded_only，实际核读后由对应精选工具登记范围。

本批原始调查是首轮样本，不宣称系统性穷尽。未来数值参考/训练数据遵循[基准契约](../benchmark-contract.md)，另建有输入/构建/参考/失败/日志/清单的版本。
