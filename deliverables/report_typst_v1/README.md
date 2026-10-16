# 课程报告初版与科研图

本目录是根据十项作业范围重新组织的独立初版，保留原报告底稿和旧图目录。正文使用现有资料、C 计算输出和研究结论，没有用研究假设补造真实型号参数。

- 阅读：[报告 PDF](report-v1.pdf)，A4，17 页。
- 修改：[Typst 正文](report.typ)。封面只填写已知课题、六位组员和日期，没有虚构学校、班级、学号或教师。
- 模板：[选型与来源](template-selection.md)，使用已网上核实的 `crd2333/template-report` 固定提交及 MIT 许可。
- 插图：[七张科研图与格式索引](figures/README.md)，每张提供矢量 SVG、嵌字体 PDF 和 450 dpi PNG。
- 追溯：[数据来源清单](data/manifest.json)、[图表清单及哈希](figures/figure-manifest.json)。

## 内容范围

封面、目录、摘要后，正文依次为：研究目标；计算方法；参数确定；程序设计思想与关键技术；程序流程图；程序说明；设计算例结果与分析；结论与感悟；参考文献；组员分工说明。何明轩和纪博闻承担主要代码工作，六人分工已按用户要求写入。

第 7 节覆盖燃烧温度与特征速度、石墨判据、甲烷/RP-1 成对比较、喷管面积与背压、定比热过膨胀诊断、历史给定温度循环及外排投影、液体入口响应、绝热循环和验证范围。历史给定热状态、绝热 HP 主线和独立定比热诊断保留各自工况。

型号构型资料复核截止仍为 2026-10-03，产品补充截止仍为 2026-10-06。报告日期和图表重绘没有刷新这些事实。

## 复现

在项目根目录执行：

```powershell
# 仅绘图：数据已经随本目录保存
python deliverables/report_typst_v1/figures/build_figures.py

# 从现有项目归档重新提取数据，不运行新的物理解算
python deliverables/report_typst_v1/figures/snapshot_inputs.py

# 编译正文；在更新图表后重新执行
typst compile deliverables/report_typst_v1/report.typ deliverables/report_typst_v1/report-v1.pdf
```

环境：Typst 0.14.2；Python、Matplotlib、NumPy 用于绘图。中文正文使用 SimSun，标题使用 SimHei，英文使用 Times New Roman，代码使用 Consolas，强调体使用 KaiTi；绘图使用 Microsoft YaHei / DejaVu Sans。换机器需安装对应字体，或在模板字体映射和绘图脚本中显式更换后复核分页。

上游模板使用已固定版本的 Typst Preview 包；初次编译可能需要联网下载，已有缓存可离线使用。编译仍会提示上游 `mitex:0.2.5` 的 `kai` 弃用警告，不影响此次 PDF；本地模板的 `diff` 旧符号已经适配。C 程序的运行依赖与上述文档工具无关。

## 数据与校核

绘图脚本只读取保存的 C 结果，不包含另一个 Python 物理求解器。扫描、拒绝点及循环质量流路来自演示页保存的 JSON，约六位有效数字；成对方法与入口差值使用归档全精度 JSON。图中离散点连线不是额外求解、插值优化或统计误差带。

本目录的 `data/` 只保留当前图表实际读取的三份 JSON 和来源清单。C 输出原件、输入、构建身份和验证归档仍保留在项目原位置。报告里的约数、额外小数位及软件残差不能当作实机精度或模型完备性的证明。

PDF 已按页渲染核对，过程与统一质量结果见[071 记录](../../taskshot/2026-10-16_071-report-typst-scientific.md)。页面渲染与旧版试排图保存在不入库的 `build/report-qa/`。本目录未改变原课件、原始来源、PPT 或旧科研图目录。
