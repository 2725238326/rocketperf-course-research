# 课程报告初版与科研图

本目录是根据十项作业范围重新组织的独立初版，保留原报告底稿和旧图目录。正文使用现有资料、C 计算输出和研究结论，没有用研究假设补造真实型号参数。

- 阅读：[报告 PDF](report-v1.pdf)，A4，本次修订为 22 页。
- 修改：[Typst 正文](report.typ)。封面只填写已知课题、六位组员和日期，没有虚构学校、班级、学号或教师。
- 模板：[选型与来源](template-selection.md)，使用已网上核实的 `crd2333/template-report` 固定提交及 MIT 许可。
- 插图：[十二张报告插图索引](figures/README.md)，包括七张科研与计算流程图、一张动态架构取帧、四张 GUI 页面；七张原图均提供 SVG、嵌字体 PDF 和 450 dpi PNG。
- 动画：[报告配套动态架构](figures/architecture-report.html)，30 s 循环；PDF 插入 24 s 静态取帧，并保留本地 HTML 链接。
- 追溯：[数据来源清单](data/manifest.json)、[科研图清单](figures/figure-manifest.json)、[架构与 GUI 展示图清单](figures/report-visuals-manifest.json)。

## 内容范围

封面、目录、摘要后，正文依次为：研究目标；计算方法；参数确定；程序设计思想与关键技术；程序流程图；程序说明；设计算例结果与分析；结论与感悟；参考文献；组员分工说明。何明轩和纪博闻承担主要代码工作，六人分工已按用户要求写入。

第 7 节覆盖燃烧温度与特征速度、石墨判据、甲烷/RP-1 成对比较、喷管面积与背压、定比热过膨胀诊断、历史给定温度循环及外排投影、液体入口响应、绝热循环和验证范围。历史给定热状态、绝热 HP 主线和独立定比热诊断保留各自工况。

第 4.4 节补入动态架构，第 6.4 节补入实际 GUI 的燃烧室、推进剂比较、喷管与循环页面。截图来自与桌面窗口相同的页面资源，通过本地 C 桥接重新计算，关闭动画并等待返回后取图。循环页为长十乙一级背景的 RP-1 富氧补燃研究情景，四个主要数值与该次 C 返回一致；旧截图和旧说明保留在原位置。GUI 截图说明界面状态，不替代科研图的数据来源或独立的科学验证。

本次润色覆盖摘要、研究目标、方法、参数解释、程序设计、算例分析和结论，调整重复否定句与审查式措辞，并保留原有数值、引用及模型限制。图表标题、章节与数据讨论按实际工况对应。

型号构型资料复核截止仍为 2026-10-03，产品补充截止仍为 2026-10-06。报告日期和图表重绘没有刷新这些事实。

## 复现

在项目根目录执行：

```powershell
# 仅绘图：数据已经随本目录保存
python deliverables/report_typst_v1/figures/build_figures.py

# 重取动态架构帧并校验保存的 GUI 图，不需 GUI 运行环境
python deliverables/report_typst_v1/figures/build_report_visuals.py

# 从现有项目归档重新提取数据，不运行新的物理解算
python deliverables/report_typst_v1/figures/snapshot_inputs.py

# 编译正文；在更新图表后重新执行
typst compile deliverables/report_typst_v1/report.typ deliverables/report_typst_v1/report-v1.pdf
```

环境：Typst 0.14.2；Python、Matplotlib、NumPy 用于绘图。中文正文使用 SimSun，标题使用 SimHei，英文使用 Times New Roman，代码使用 Consolas，强调体使用 KaiTi；绘图使用 Microsoft YaHei / DejaVu Sans。换机器需安装对应字体，或在模板字体映射和绘图脚本中显式更换后复核分页。

展示图脚本另用 Pillow 和 Playwright/Chromium。冻结的动态 HTML 已随报告保存，常规复现不必修改项目原架构页。若需从原页刷新，显式添加 `--refresh-architecture` 并重新检查帧。GUI 源码位于独立工作树，示例刷新命令如下；路径应按实际环境调整，不以历史截图代替新的 C 调用：

```powershell
python deliverables/report_typst_v1/figures/build_report_visuals.py `
  --gui-root ../火发原理-gui `
  --bridge ../火发原理-gui/build/gui/gui_bridge_stdio.exe
```

上游模板使用已固定版本的 Typst Preview 包；初次编译可能需要联网下载，已有缓存可离线使用。编译仍会提示上游 `mitex:0.2.5` 的 `kai` 弃用警告，不影响此次 PDF；本地模板的 `diff` 旧符号已经适配。C 程序的运行依赖与上述文档工具无关。

## 数据与校核

绘图脚本只读取保存的 C 结果，不包含另一个 Python 物理求解器。扫描、拒绝点及循环质量流路来自演示页保存的 JSON，约六位有效数字；成对方法与入口差值使用归档全精度 JSON。图中离散点连线不是额外求解、插值优化或统计误差带。

本目录的 `data/` 只保留当前图表实际读取的三份 JSON 和来源清单。C 输出原件、输入、构建身份和验证归档仍保留在项目原位置。报告里的约数、额外小数位及软件残差不能当作实机精度或模型完备性的证明。

初版过程见[071 记录](../../taskshot/2026-10-16_071-report-typst-scientific.md)，本次动态架构、GUI 与行文修订的页面审阅和统一质量结果见[072 记录](../../taskshot/2026-10-16_072-report-gui-architecture-polish.md)。页面渲染、C 桥接原始返回和试排图保存在不入库的 `build/report-qa/`。本目录未改变原课件、原始来源、PPT、原 Markdown 报告或旧科研图目录。
