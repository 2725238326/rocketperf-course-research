# PPT 内容结构方案（12 正文页 + 6 附录页）

给做 PPT 的组员：每页放什么内容、表格列数、图的位置。页面文字照抄 [presentation.md](presentation.md) 对应页（完整的表和要点都在那里），数字不改。模板在 `PPT/` 里选一个白底 16:9 模板。

---

## 全局规范

- 白底 16:9，正文表格和要点 ≥18 pt（投影后排要看清）
- 每页顶部大标题 = 结论（presentation.md 里加粗的标题），32–36 pt
- 右下角小字页码
- 无 PPT 动画效果（唯一动的是演示页）
- 数字格式：小数点后位数照 presentation.md，不多不少

---

## 正文页（P1–P12）

### P1 封面
标题 + 副题 + 组号组员日期。右下角一行小字：`C17 计算核心 · 13772 项检查 · 2148 项 CEA 字段对照`。

### P2 问题（表格 + 清单框）
左右分栏，左 60%：四行构型表（presentation.md P2）。右 40%：缺的输入清单框（六项：室压/喉面积/面积比/混合比/入口温压/循环分流）。底部来源截止日期。

### P3 五个工作点（五行要点）
五行大字要点，前四字加粗。行间留空。

### P4 方法（流程图 + 公式）
上半 60% 放 `docs/architecture/report-flow.svg` 截图。下半三个公式横排大字：`c*=Pc·At/ṁ`、`F=CF·Pc·At`、`Isp=F/(ṁ·g0)`，公式下各一行小注。

### P5 燃烧室与积碳（表 + 组成图）
左侧表格（O/T/c*/a_C/状态 五列四行）。右侧放 `deliverables/demo/screenshots/p5_chamber.png` 裁剪组成图部分。

### P6 推进剂（对比表 + 相对差图）
上半五列对比表。下半右侧嵌 `p6_propellant.png` 右半的相对差图。

### P7 面积比（表 + 收益图）
四列表居中。右侧 `docs/area-ratio-tradeoff.svg` 截图。要点两条：收益腰斩、背压损失翻倍。

### P8 海平面过膨胀（表 + 留白）
左侧表（pe/pa·pe⁻¹/匹配面积比/0.4pa 参考值）。右侧留白（演示时切出去）。

### P9 循环（精简对比表）
两列对比表（5 行，只放前提参数）。这页是引子，讲到这里切演示页 4。

### P10 五条判断（三列大表）
三列（编号/判断/依据），五行。关键数字标粗：−4.46%、腰斩、23 s、0.91%、0.883。

### P11 验证（检查表 + 散点图）
左侧五项检查表。右侧 `p11_cea.png` 散点区（红线是容差）。

### P12 边界（两列）
左边五条技术边界（每条一行）。右边"下一步"两行 + 分工一行。最后一行"谢谢各位老师"。

---

## 附录页（P13–P18，备份截图）

六张 1920×1080 截图整页放，每页顶部小标题"备份 · 演示页 X 同状态截图"。正常答辩不翻；演示出问题或 Q&A 追问细节时翻到对应附录页指图。

| 附录页 | 截图文件 | 内容 |
|---|---|---|
| P13 | p5_chamber.png | 燃烧室组成 + 活度线（O/F 2.6） |
| P13b | p5_chamber_carbon_refusal.png | 凝聚碳拒算态（待补截） |
| P14 | p6_propellant.png | 比冲曲线 + 相对差 |
| P14b | p6_propellant_crossover.png | 推力差变号点 O/F 2.9（待补截） |
| P15 | p8_nozzle_refusal.png | 海平面 ε40 拒算态 |
| P16 | p9_cycle.png | 开式循环 + 四本账 |
| P16b | p9_cycle_staged.png | 补燃循环态（待补截） |
| P17 | p11_cea.png | CEA 对照散点 |
| P18 | p11b_engineering.png | 工程三句话 |

**待补截的三张**见 `deliverables/demo/screenshots/README.md`，主讲演练第一遍时按清单操作截取。

---

## 素材清单

| 文件位置 | 用途 |
|---|---|
| `deliverables/demo/screenshots/*.png` | 六张默认态 + 三张关键态（待补） |
| `docs/architecture/report-flow.svg` | P4 流程图 |
| `docs/area-ratio-tradeoff.svg` | P7 收益图 |
| [presentation.md](presentation.md) | 每页的表格和文字内容（照抄） |

---

## 验收

PPT 完成后：
1. 每页数字对着 presentation.md 表格核一遍
2. 检查字号：任何正文 < 18 pt 的改大
3. 投影预览：后排能看清表格最小的数字
4. 交给主讲按 [defense-script.md](defense-script.md) 完整计时一遍
