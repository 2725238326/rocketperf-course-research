# 课程研究报告

本报告围绕朱雀三号遥一与长征十号乙首飞构型，按课程要求组织为十项正文内容，并使用已核实的 Typst 课程报告模板排版。型号信息来自公开资料，性能分析列明相应的研究输入与计算条件。

- 阅读：[审查修订版 PDF](report-reviewed.pdf)，A4 版式，20 页；[2026-10-17 原定稿](report-final.pdf)保留。
- 编辑：[修订版 Typst 正文](report-reviewed.typ)，[原定稿正文](report.typ)保留。封面列明课题、六位组员与报告日期。
- 模板：[选型与来源](template-selection.md)，采用固定版本的 MIT 许可报告模板并按课程报告需求适配。
- 插图：[报告插图索引](figures/README.md)，含科研曲线、计算流程、动态架构取帧和四张 GUI 页面。
- 原稿动态展示：[架构动画](figures/architecture-report.html)保留；修订版第4.4节改用明确表示依赖方向的模块图，不再附动画。
- 数据追溯：[计算数据来源](data/manifest.json)、[科研图清单](figures/figure-manifest.json)、[架构与 GUI 图清单](figures/report-visuals-manifest.json)。

## 报告结构

正文依次为研究目标、计算方法、参数确定、程序设计思想与关键技术、程序流程图、程序说明、设计算例结果与分析、结论与感悟、参考文献、组员分工说明。代码核心工作由何明轩和纪博闻承担，其余组员分别负责资料、参数、数据和报告整理。

结果部分包括甲烷燃烧与石墨稳定性、甲烷和固定 RP-1 方法比较、喷管面积比与背压、给定热状态循环的外排方向、液体入口响应、绝热循环以及软件和模型核验。给定热状态循环、绝热 HP 循环和定比热诊断使用各自的输入和模型定义。

修订版第 4 节展示模块调用关系，第 6 节使用 `figures/reviewed/` 的四张新截图，展示燃烧、推进剂比较、喷管诊断和循环页面。GUI 用于说明操作界面；定量结果来自计算程序的研究算例输出。组员分工未在本次审查中调整。

构型资料核对截至 2026-10-03，产品和试验资料补充至 2026-10-06。

## 复现

在项目根目录运行：

```powershell
# 根据本目录保存的数据重绘科研图
python deliverables/report_typst_v1/figures/build_figures.py

# 校验动态架构帧与已保存的 GUI 图
python deliverables/report_typst_v1/figures/build_report_visuals.py

# 从项目现有归档提取图表输入，不启动新的物理解算
python deliverables/report_typst_v1/figures/snapshot_inputs.py

# 编译审查修订版（从项目根目录执行）
typst compile --root . deliverables/report_typst_v1/report-reviewed.typ deliverables/report_typst_v1/report-reviewed.pdf
```

环境：Typst 0.14.2；绘图使用 Python、Matplotlib 与 NumPy。正文依赖 SimSun、SimHei、Times New Roman、Consolas 和 KaiTi 字体；换机编译时如字体映射不同，应复核分页与中文渲染。

动态展示图使用 Pillow 和 Playwright/Chromium。冻结的 HTML 已随报告保存，日常复现不需要运行 GUI。若从 GUI 更新截图，应连接当前版本的本地 C 桥接程序并等待计算完成后取图。

## 数据和结果说明

绘图脚本读取保存的 C 计算结果。离散点对应实际计算网格，连线用于辅助观察变化趋势；扫描曲线按约六位有效数字显示。

NASA CEA 对照与 C 实现使用部分相同的热化学数据，主要用于检查相同数据和物种范围内的计算一致性。对实机性能的评估还需真实燃料、供给状态、损失模型及同工况试验数据。

本目录的 `data/` 保存插图使用的数据及其来源清单；完整输入、输出和验证记录另行保存。

