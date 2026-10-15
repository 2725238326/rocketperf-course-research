# 交付物索引

所有文件均在本目录 (`deliverables/`) 下，直接双击打开或按说明查阅。

---

## 核心交付物（3 件）

### 1. [report.md](report.md)
**研究报告**，10 节，204 行。涵盖：问题与动机、方法、四组结果（燃烧室与积碳边界、推进剂取舍、喷管面积比、循环三本账）、五条判断、验证、技术边界、参考文献。全部数字均可回 `results/` 或代码复现。

### 2. [demo/index.html](demo/index.html)
**离线单文件演示页**（710 KB），6 个标签页：
- 1 燃烧室与积碳边界
- 2 推进剂取舍
- 3 面积比与背压
- 4 循环三本账
- 5 CEA 对照
- 6 工程与质量

**操作**：双击打开，键盘 1–6 切页，A 键开关动画。全部数值来自 2501 次 C 调用（已测 Release 版），`python tools/demo_data.py --check` 可重跑核对。

### 3. [presentation.md](presentation.md)
**15 分钟答辩大纲**，12 页，290 行。包含：每页标题（即结论）、表格（加注释列/单位/边界条件）、要点、讲稿、演示操作清单、30 项 Q&A 预案（含 14 条理论追问口径答案）。时间预算 825 秒主体 + 75 秒余量。

---

## 答辩支持文档（5 件）

### 4. [defense-script.md](defense-script.md)
**逐字稿**（去 AI 腔版），2973 字 / 825 秒 = 3.60 字/秒。含：
- 12 页完整台词（每页标注秒数）
- 演示应急表（页面打不开/交互卡死/投影字小/忘词）
- 3 级删减预案（超时先删 P8 演示 → P5 演示 → P11）
- 演练安排（今晚通读 → 第一遍计时 → 第二遍抽问 → 演示机检查 → 当天提前 15 分钟）
- 一页卡（主线/公式/关键数字/边界/应答原则）
- **14 条理论追问口径答案**（每条 30 秒：冻结流/声速喉部/等熵假设/HP vs 定熵/c\* 峰偏移/平衡常数/九物种/液体焓/泵功/瞬态/摇摆/O/F 假设/比冲口径/判断一致性）

### 5. [ppt-structure.md](ppt-structure.md)
**PPT 内容结构方案**（给制作 PPT 的组员）。18 页规格：
- 12 页正文 + 6 页附录备份截图
- **每页 ASCII wireframe**（标题/表格/图位置、左右分栏比例 60/40 或 50/50、信息密度高/中/低、视觉重心标注）
- 素材清单（6 张默认态 + 3 张关键态截图、流程图 SVG、收益图 SVG）
- 验收标准（数字核对、字号 ≥18 pt、投影预览）

### 6. [demo-choreography.md](demo-choreography.md)
**演示编排指南**（给主讲）。规定：
- 窗口准备（浏览器 + PPT 窗口化放映 + Alt+Tab 切换）
- 四页演示切换时间表（P5 30s / P6 40s / P8 40s / P9 90s）
- **每页演示详细手势**（"**[指左上 KPI 6.82×10⁻⁵]**"、"**[手指沿外排管线从预燃室指向独立喷管]**"）
- 翻车三级保底（交互卡住刷新 → 用 PPT 数字讲 → 翻附录页指图）
- 附录页使用时机（演示翻车 + Q&A 追问细节）
- 演练清单（7 步，含补截三张关键态）

### 7. [timing-chart.md](timing-chart.md)
**0–900 秒可视化时间轴**。ASCII 图标出：
- 12 页映射到 30 秒间隔网格
- 四段演示位置（200 秒占 24%）
- 三级删减触发点（退到 785s → 755s → 715s）
- 密度分布（4:00–10:30 高密度核心 410s 占 50%）
- 关键节点表（0:00 开场 → 13:45 正常结束）

### 8. [demo/screenshots/README.md](demo/screenshots/README.md)
**关键演示态截图清单**。六张默认态已有，**三张关键态待补截**（主讲演练第一遍时操作）：
- p5_chamber_carbon_refusal.png（凝聚碳拒算，点"凝聚碳区"）
- p6_propellant_crossover.png（推力差变号 O/F 2.9）
- p9_cycle_staged.png（补燃循环 17.95 MPa）

每张标注操作步骤、验证要点、PPT 附录页用途。

---

## 其他交付物（1 件）

### 9. [contributions.md](contributions.md)
**组员分工说明**。三个方案（按产物类型 / 按时间段 / 主讲+两支持），每个方案标注工作量（3–6 小时）。实际分工表待组内填写、本人确认。验收标准：PPT 18 页、演练 <14:30、quality.py 通过。

技术附录在仓库 [docs/propellant-method-comparison.md](../docs/propellant-method-comparison.md)：同喉面积口径、入口状态差异、RP-1 锚点方法、推力差随 O/F 变号机理、贮箱体积未算。

---

## 文档间关系

```
presentation.md (答辩大纲，825 秒)
    ├── defense-script.md (逐字稿 2973 字 + 14 条 Q&A 口径)
    ├── ppt-structure.md (18 页版式 wireframe)
    │   └── demo/screenshots/*.png (9 张截图：6 默认 + 3 关键)
    ├── demo-choreography.md (4 页演示手势 + 翻车保底)
    └── timing-chart.md (0–900s 时间轴 + 密度分布)

report.md (10 节研究报告)
    └── demo/index.html (2501 次 C 调用嵌入)

contributions.md (分工方案 + 验收标准)
```

---

## 使用顺序（15 分钟答辩准备流程）

1. **今晚**：组内协商选一个 [contributions.md](contributions.md) 方案，分配角色
2. **制作 PPT**：按 [ppt-structure.md](ppt-structure.md) 排 18 页，数字照抄 [presentation.md](presentation.md)
3. **演练第一遍**：主讲按 [defense-script.md](defense-script.md) 完整走，边演示边按 [demo/screenshots/README.md](demo/screenshots/README.md) 补截三张关键态
4. **演练第二遍**：从 [presentation.md](presentation.md) Q&A 表随机抽 3 个问题当场答，参考 [defense-script.md](defense-script.md) 末尾的 14 条口径答案
5. **演示机测试**：拷贝 [demo/index.html](demo/index.html) 到演示机双击打开，F11 全屏确认无滚动条
6. **答辩当天**：提前 15 分钟按 [demo-choreography.md](demo-choreography.md) 窗口准备清单操作，页面停页 1，PPT 停封面

---

## 验收

- **文档完整性**：9 件交付物全部存在
- **数字一致性**：PPT 每页数字与 [presentation.md](presentation.md) 表格核对无误
- **时间控制**：演练第一遍 < 14:30（超时执行 [defense-script.md](defense-script.md) 删减预案）
- **质量门通过**：`python tools/quality.py` 绑定最终证据，无报错

全部验收通过后，可提交。
