"""Editable SVG that connects the coursework to evidence and implemented models."""

from html import escape


WIDTH, HEIGHT = 1920, 1480
INK, MUTED = "#172d46", "#53697d"
BLUE, TEAL, AMBER = "#245dc2", "#087f83", "#a56215"
LINE, BG = "#cfdae6", "#f3f6fa"


def text(x, y, value, size=21, color=INK, weight=400):
    return (
        f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" '
        f'font-weight="{weight}">{escape(value)}</text>'
    )


def lines(x, y, values, size=21, color=MUTED, gap=31):
    return "".join(text(x, y + i * gap, v, size, color) for i, v in enumerate(values))


def rect(x, y, w, h, fill="#ffffff", stroke=LINE, radius=14):
    return (
        f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" '
        f'fill="{fill}" stroke="{stroke}" stroke-width="1.4"/>'
    )


def link(target, content):
    return f'<a href="{escape(target, quote=True)}">{content}</a>'


def flow(x1, y1, x2, y2, color=BLUE, dashed=False):
    dash = ' stroke-dasharray="7 6"' if dashed else ""
    return (
        f'<path d="M{x1},{y1} L{x2},{y2}" stroke="{color}" '
        f'stroke-width="2.4" fill="none" marker-end="url(#flow-arrow)"{dash}/>'
    )


def requirement(x, number, title, detail, ids):
    return link(
        "../requirements-map.md",
        rect(x, 210, 576, 145)
        + text(x + 24, 250, number, 23, BLUE, 650)
        + text(x + 75, 251, title, 27, INK, 650)
        + text(x + 24, 293, detail, 21, MUTED)
        + text(x + 24, 330, ids, 17, BLUE, 600),
    )


def calculation_node(x, y, w, title, body, footer, color=BLUE, fill="#ffffff"):
    return (
        rect(x, y, w, 143, fill, color, 10)
        + text(x + 18, y + 34, title, 23, INK, 650)
        + lines(x + 18, y + 68, body, 19, MUTED, 27)
        + text(x + 18, y + 124, footer, 16, color, 600)
    )


def assignment():
    """No live task status or completion percentages: this is a capability map."""
    body = rect(0, 0, WIDTH, HEIGHT, BG, BG, 0)
    body += text(60, 48, "ROCKETPERF  /  COURSEWORK × SYSTEM DESIGN", 17, BLUE, 650)
    body += text(60, 108, "从作业要求到可验证的动力系统研究", 43, INK, 700)
    body += text(60, 151, "研究对象：朱雀三号 · 长征十号乙   ｜   按级段、子型和工况分别比较", 24, MUTED)
    body += text(60, 188, "老师要求回答三个问题；软件服务于研究，不以模块数量代替结论。", 20, MUTED)
    body += requirement(60, "01", "调查工作方案与能力", "先核对对象和公开证据，再确定能比较什么。", "老师要求  REQ-01 · REQ-04")
    body += requirement(672, "02", "用基本理论分析性能", "C语言自动计算，交代输入、方法和适用条件。", "老师要求  REQ-02 · REQ-05 · REQ-06")
    body += requirement(1284, "03", "研究优缺点及可能改进", "包含计算，同时说明收益、代价和局限。", "老师要求  REQ-03")

    # Evidence → computation → interpretation. Lane widths allow readable CJK.
    body += flow(249, 355, 249, 404)
    body += flow(960, 355, 960, 404)
    body += flow(1671, 355, 1671, 404)
    body += rect(60, 410, 378, 575)
    body += link("../../调研/README.md", text(84, 454, "证据与参数", 29, INK, 650))
    body += text(84, 488, "两型分别建账，不拼接参数", 20, TEAL, 600)
    body += lines(84, 542, ["原文与日期", "级段 · 子型 · 批次", "原单位 · 工况 · 系统边界"], 22, INK, 34)
    body += '<line x1="84" y1="637" x2="414" y2="637" stroke="#cfdae6"/>'
    body += lines(84, 678, ["事实：可定位的原文", "派生：公式与输入可复核", "假设：单独标注用途", "未知：留空，不自动补数"], 21, MUTED, 35)
    body += link("../research-reference-coverage.md", text(84, 854, "真实型号输入仍有缺口", 21, AMBER, 650))
    body += lines(84, 892, ["缺参数不阻断方法验证", "但不能输出型号绝对性能"], 20, MUTED, 31)

    body += flow(438, 678, 488, 678)
    body += rect(494, 410, 932, 575, "#edf3fd", "#b6c9e9")
    body += link("../engineering.md", text(520, 454, "C17 计算核心", 29, INK, 650))
    body += text(520, 488, "项目实现选择：零维 / 准一维 / 稳态；不是有限元或CFD", 20, MUTED)
    body += calculation_node(520, 518, 250, "物性与燃烧状态", ["气态 / 固定液态焓HP", "九物种气相产物NASA9"], "固定锚点 · 非液体EOS")
    body += calculation_node(821, 518, 250, "冻结喷管", ["温变物性 / 阻塞通量", "流量 · c* · 推力 · 比冲"], "给定流量 / 固定喉面积")
    body += calculation_node(1122, 518, 278, "单点与扫描结果", ["状态 · 残差 · 越域原因", "尺寸 · 同条件性能变化"], "成功与失败都保留")
    body += flow(770, 589, 815, 589)
    body += flow(1071, 589, 1116, 589)
    body += calculation_node(520, 700, 250, "恒密度泵与轴功", ["压升 / 密度 / 效率", "泵功 → 支路流量"], "入口焓与密度显式给定", TEAL)
    body += calculation_node(821, 700, 250, "给定热状态外排", ["发生器TP → 冻结涡轮", "分流后主室TP → 喷管"], "受限原型 · 不支持回流", TEAL)
    body += calculation_node(1122, 700, 278, "整机口径与热边界", ["两路轴向推力 / 总消耗", "维持状态所需热交换"], "倒算热量 ≠ 冷却负荷", TEAL)
    body += flow(770, 771, 815, 771, TEAL)
    body += flow(1071, 771, 1116, 771, TEAL)
    body += text(520, 888, "自动执行：严格参数输入 → CLI编排 → 纯C求解 → JSON / 运行记录", 21, INK, 600)
    body += text(520, 927, "Python仅管理、复核和绘图；定比热旧模型保留为教学 / 回归基准。", 20, MUTED)
    body += text(520, 960, "HP支持固定液态反应物锚点；循环仍给定热状态，不是绝热整机闭合。", 20, AMBER, 600)

    body += flow(1426, 678, 1476, 678)
    body += rect(1482, 410, 378, 575)
    body += link("../improvement-analysis.md", text(1506, 454, "研究分析", 29, INK, 650))
    body += text(1506, 488, "比较必须使用相同条件", 20, TEAL, 600)
    body += lines(1506, 542, ["喷管面积比与环境背压", "支路排气的轴向贡献", "效率与输入的局部响应"], 21, INK, 34)
    body += '<line x1="1506" y1="637" x2="1836" y2="637" stroke="#cfdae6"/>'
    body += lines(1506, 678, ["量化：推力 / 比冲收益", "同时报告：出口尺寸代价", "说明：固定几何或重新定尺寸", "指出：模型域与缺失物理"], 20, MUTED, 35)
    body += text(1506, 854, "已有合成研究，不是型号改装", 21, AMBER, 650)
    body += lines(1506, 892, ["局部扰动不是置信区间", "条件性趋势不是实测结论"], 20, MUTED, 31)

    # A common evidence gate under all research lanes.
    body += rect(60, 1017, 1800, 119, "#e8f4f2", "#bad9d3", 12)
    body += text(84, 1058, "共同验证", 25, TEAL, 650)
    for x, title, detail in [
        (286, "解析极限与守恒", "物理关系 / 失败输出保持"),
        (674, "固定NASA9 / CEA对照", "同源物性，不是实验验证"),
        (1102, "完整计算记录", "输入 / 状态 / 构建与哈希"),
        (1490, "固定版本复跑", "软件PASS ≠ 科学结论"),
    ]:
        body += text(x, 1058, title, 22, INK, 600)
        body += text(x, 1100, detail, 19, MUTED)

    body += text(60, 1181, "最终交付", 27, INK, 650)
    body += text(263, 1181, "老师要求 REQ-07—REQ-11  ｜  当前先完成研究与计算，PPT和最终报告后置", 20, MUTED)
    for x, title, detail, tag, planned in [
        (60, "程序源代码", "C核心 · 输入 · 测试 · 构建说明", "已有阶段产物", False),
        (522, "程序发布版", "Windows控制台即可 · 可复跑", "阶段交接 ≠ 最终发布", False),
        (984, "展示PPT", "2026-10-16 第3—5节", "展示≤10分钟 · 提问≤5分钟", True),
        (1446, "研究报告", "要求的10项内容 · 真实人员分工", "结论与引用须对应实际程序", True),
    ]:
        body += rect(x, 1205, 414, 127, "#fffaf1" if planned else "#ffffff", "#e5cda9" if planned else LINE, 12)
        body += text(x + 22, 1242, title, 25, INK, 650)
        body += text(x + 22, 1276, detail, 19, MUTED)
        body += text(x + 22, 1309, tag, 17, AMBER if planned else BLUE, 600)
    body += text(60, 1376, "尚未覆盖", 22, AMBER, 650)
    body += text(211, 1376, "液体EOS / 煤油 · 全循环硬件与绝热闭合 · 冷却 / 分离 / 寿命 · 两型真实参数和整机独立参考", 21, MUTED)
    body += '<line x1="60" y1="1410" x2="1860" y2="1410" stroke="#cfdae6"/>'
    body += link("../../作业要求/大作业1_要求存档.md", text(60, 1448, "要求依据：用户照片转录与课件差异记录；未指定有限元、CFD、GUI或CEA。", 17, MUTED))
    body += text(1070, 1448, "两型直接原文核验截至2026-10-03；本图不刷新线上事实。", 17, MUTED)
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{WIDTH}" height="{HEIGHT}" '
        f'viewBox="0 0 {WIDTH} {HEIGHT}" role="img" aria-labelledby="assignment-title assignment-desc">'
        '<title id="assignment-title">作业要求与动力系统研究架构</title>'
        '<desc id="assignment-desc">三条课程研究主线对应证据参数、C17计算和条件性改进分析；'
        '共同验证支撑四项交付，并明确固定液态锚点不等于液体EOS、真实型号或完整循环。</desc>'
        '<defs><marker id="flow-arrow" markerWidth="7" markerHeight="7" refX="6" refY="3.5" orient="auto">'
        '<path d="M0,0 L7,3.5 L0,7 Z" fill="#53697d"/></marker></defs>'
        '<g font-family="Microsoft YaHei,Noto Sans CJK SC,Arial,sans-serif">'
        + body
        + "</g></svg>\n"
    )


MERMAID = """flowchart TD
  A[REQ-01 调查两型工作方案与能力] --> E[证据与参数：版本 / 工况 / 来源 / 未知]
  B[REQ-02 C语言理论性能计算] --> C[C17：NASA9 / TP与HP / 冻结喷管 / 给定热状态外排]
  R[REQ-03 优缺点与可能改进，含计算] --> I[条件性收益 / 尺寸代价 / 输入响应]
  E --> C --> I
  C --> V[解析关系 / 固定软件对照 / 保存结果与哈希 / 复跑]
  I --> V
  V --> D[REQ-07至REQ-11：源码 / 发布版 / PPT / 报告]
  V -. 证据或范围不足 .-> E
  U[未覆盖：液体EOS与煤油 / 全循环硬件 / 冷却分离寿命 / 型号独立参考] -. 限制结论 .-> I
"""
