"""Coursework requirements → method → results, then verification and deliverables (16:9 SVG)."""

from diagram_kit import (BODY, INK, MUTED, NAVY, OCHRE, TEAL, TONE, ZONE, arrow, card, document,
                         header, link, rect, text, zone)

WIDTH, HEIGHT = 1920, 1080
COL_X, COL_W = [80, 680, 1280], 560

COLUMNS = [
    ("01", "调查工作方案与能力", "REQ-01 · REQ-04", "../../调研/README.md",
     ["按级段分别整理公开资料", "每个参数记出处、日期、子型、工况"],
     ["朱雀三号遥一：一级 **9 × TQ-12A**", "　二级 **1 × TQ-15A** 真空型",
      "长征十号乙首飞：一级 **7 台液氧煤油**", "　二级 **液氧甲烷**"],
     "无同批单机性能参数，不给型号绝对性能"),
    ("02", "用基本理论计算性能", "REQ-02 · REQ-05 · REQ-06", "../engineering.md",
     ["C17：NASA9 物性 → HP 平衡求燃温", "冻结喷管 → 流量、推力、比冲"],
     ["Pc 10 MPa、面积比 10、真空", "　甲烷 Isp **324.4 s**，RP-1 **310.6 s**",
      "一级开式 / 补燃情景", "　推力 **290.5 / 285.5 kN**"],
     "输入为研究假设，不是发动机标定数据"),
    ("03", "优缺点与可能改进", "REQ-03", "../improvement-analysis.md",
     ["固定其余输入，每次只改一个因素", "收益与代价同时给出"],
     ["同喉面积：甲烷 Isp **+13.9 s**，推力 **−0.20%**", "面积比 10→40：Isp **+23.4 s**",
      "　代价：出口面积 **× 4**", "富燃发生器 O/F **0.9～1.0** 触及积碳边界"],
     "未计算喷管质量、冷却、流动分离"),
]

CHECKS = [("解析解", "L0 喷管、泵功与公式一致"), ("CEA 同源对照", "液甲烷燃温最大差 **0.0044 K**"),
          ("守恒残差", "质量 · 元素 · 焓 · 轴功"), ("可复跑", "输入、构建版本、输出哈希")]
DELIVER = [("程序源代码", "C17 核心与测试"), ("发布版", "Windows 控制台"),
           ("展示 PPT", "10 月 16 日 · 15 分钟"), ("研究报告", "10 项内容 · 分工")]


def column(x, number, title, ids, target, method, results, gap):
    out = zone(x, 146, COL_W, 584, "navy")
    out += text(x + 24, 196, number, 34, NAVY, 700)
    out += link(target, text(x + 80, 194, title, 24, INK, 700, limit=COL_W - 104))
    out += text(x + 80, 222, ids, 14, MUTED)
    out += card(x + 20, 246, COL_W - 40, 132, "slate", "方法", method, 17, 30)
    out += card(x + 20, 394, COL_W - 40, 236, "teal", "结果", results, 17, 36)
    out += rect(x + 20, 646, COL_W - 40, 64, ZONE["ochre"], TONE["ochre"], 6, width=1)
    out += text(x + 40, 672, "未覆盖", 13, OCHRE, 700)
    out += text(x + 40, 698, gap, 16, BODY, limit=COL_W - 80)
    return out


def assignment():
    body = header("作业要求与完成情况", "朱雀三号 · 长征十号乙：三项研究要求的方法与计算结果，经统一验证后形成四项交付", WIDTH)
    for x, spec in zip(COL_X, COLUMNS):
        body += column(x, *spec)
        body += arrow([(x + COL_W / 2, 730), (x + COL_W / 2, 770)])

    body += zone(80, 774, 1760, 110, "teal")
    body += text(108, 838, "验证", 22, TEAL, 700)
    for i, (t, d) in enumerate(CHECKS):
        cx = 260 + i * 400
        body += text(cx, 818, t, 18, INK, 700)
        body += text(cx, 852, d, 16, BODY, limit=370)
    body += arrow([(960, 884), (960, 916)])

    body += zone(80, 920, 1760, 110, "slate")
    body += text(108, 984, "交付", 22, NAVY, 700)
    for i, (t, d) in enumerate(DELIVER):
        cx = 260 + i * 400
        body += card(cx, 938, 370, 74, "navy", t, [])
        body += text(cx + 18, 1002, d, 15, BODY, limit=330)
    body += link("../../作业要求/大作业1_要求存档.md",
                 text(1840, 1062, "数值为给定假设下的程序结果，输入见报告第 3、7 节　·　要求原文：作业要求/大作业1_要求存档.md　·　交付 REQ-07～11",
                      13, MUTED, anchor="end"))
    return document("assignment", WIDTH, HEIGHT, "作业要求与完成情况",
                    "三项作业要求（REQ-01至REQ-06）各自的方法、结果与未覆盖内容；经解析解、CEA同源对照、守恒残差与复跑验证；"
                    "四项交付（REQ-07至REQ-11）：程序源代码、发布版、展示 PPT、研究报告。",
                    body)


MERMAID = """flowchart TD
  A[REQ-01/04 调查两型工作方案与能力] --> E[按级段整理：出处 / 日期 / 子型 / 工况]
  B[REQ-02/05/06 用基本理论计算性能] --> C[C17：NASA9 → HP平衡 → 冻结喷管 → 推力]
  R[REQ-03 优缺点与改进，含计算] --> I[固定其余输入，单因素比较]
  E --> C --> I
  C --> V[验证：解析解 / CEA同源对照 / 守恒残差 / 归档复跑]
  I --> V
  V --> D[REQ-07至11：源代码 / 发布版 / PPT / 报告]
  U[未覆盖：喷管质量 / 冷却 / 流动分离 / 型号实测参数] -. 限制结论 .-> I
"""
