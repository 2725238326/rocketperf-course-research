# 首轮采集数据

原文下载与调查数据分别保存，以下JSON是可复核的结构化记录，不是发动机性能卡或AI训练集。

| 文件 | 用途 |
|---|---|
| [source-index.json](source-index.json) | URL/最终URL、获取时间、HTTP/可得性、路径、SHA256/大小、发现途径与实际核读范围；保留失败 |
| [claims.json](claims.json) | 已核事实、派生、假设及来源/定位/局限；生成回答不直接升级为事实 |
| [software-catalog.json](software-catalog.json) | 固定版本、核心语言、许可、C接口区别与本批使用范围 |
| [parameter-observations.json](parameter-observations.json) | 子型/批次/工况/原单位与参数/未知观察；未知值为null |
| [thermo-comparison.json](thermo-comparison.json) | 两份原始数据库的选定10种气体字段对比，非整库等价或独立物性验证 |
| [coverage.json](coverage.json) | 实际覆盖、数量、未解决问题与零新求解/训练/GPU运行事实 |

原件位于上级raw日期目录，失败记录保留在索引；HTTP200也可能只是挑战页（W2-A03），可保存但不能支持科学结论。两个本地既有物性来源按原路径复用，没有复制或改写。

`tools/work2_survey_data.py`维护本批精选结构化条目并生成claims/software/parameters/coverage及物性对比；用 `python tools/work2_survey_data.py --check`核对漂移。`python tools/work2_research.py verify`和根统一质量检查原文哈希、来源引用、未知数值及精选数据一致性。更新精选字段须改生成源并再生，不只手改JSON。

获取新原文用 `python tools/work2_research.py fetch W2-IDNN URL --kind html`（按实际类型选择），唯一ID、原文不可覆盖，索引原子更新。研究状态“已保存”“已读相关节”“数值复现”“物理验证”保持区别，实际读过的范围才写入read_scope。

本批原始调查是首轮样本，不宣称系统性穷尽。未来数值参考/训练数据遵循[基准契约](../benchmark-contract.md)，另建有输入/构建/参考/失败/日志/清单的版本。
