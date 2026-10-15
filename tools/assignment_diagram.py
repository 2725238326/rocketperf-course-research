"""Coursework requirements → method → results, then verification and deliverables (16:9 dark SVG)."""

from diagram_style import (BASE, COMPUTE, CYCLE, FG, INPUT, NOTE, OUTPUT, VERIFY, document, edge, line, rect,
                          rich, text)
from diagram_kit import link

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
    out = rect(x, 112, COL_W, 618, "#333", "#202020", 10)
    out += text(x + 24, 160, number, 30, INPUT, 700, mono=True)
    out += link(target, text(x + 80, 158, title, 24, FG, 700, limit=COL_W - 104))
    out += text(x + 80, 184, ids, 14, NOTE, mono=True)
    out += rect(x + 20, 206, COL_W - 40, 140, INPUT, "#2d2d2d", 8, 1.5)
    out += text(x + 40, 236, "方法", 16, INPUT, 700) + line(x + 40, 250, x + COL_W - 40, 250, "#3c3c3c")
    for i, row in enumerate(method):
        out += rich(x + 40, 282 + i * 30, row, 17, FG, limit=COL_W - 80)
    out += rect(x + 20, 362, COL_W - 40, 232, COMPUTE, "#2d2d2d", 8, 1.5)
    out += text(x + 40, 392, "结果", 16, COMPUTE, 700) + line(x + 40, 406, x + COL_W - 40, 406, "#3c3c3c")
    for i, row in enumerate(results):
        out += rich(x + 40, 442 + i * 38, row, 17, FG, COMPUTE, limit=COL_W - 80)
    out += rect(x + 20, 610, COL_W - 40, 100, CYCLE, "#2d2d2d", 8, 1.5, "5 4")
    out += text(x + 40, 644, "未覆盖", 15, CYCLE, 700)
    out += text(x + 40, 680, gap, 16, FG, limit=COL_W - 80)
    return out


def assignment():
    body = (text(80, 58, "作业要求与完成情况", 32, FG, 700)
            + text(80, 90, "朱雀三号 · 长征十号乙：三项研究要求的方法与计算结果，经统一验证后形成四项交付", 18, NOTE)
            + line(80, 100, 1840, 100, "#333"))
    for x, spec in zip(COL_X, COLUMNS):
        body += column(x, *spec)
        body += edge([(x + COL_W / 2, 730), (x + COL_W / 2, 768)])
    body += rect(80, 772, 1760, 112, VERIFY, "#241f27", 10, 1.5)
    body += text(108, 836, "验证", 22, VERIFY, 700)
    for i, (t, d) in enumerate(CHECKS):
        cx = 240 + i * 404
        body += text(cx, 816, t, 18, FG, 700) + rich(cx, 850, d, 16, NOTE, VERIFY, limit=370)
    body += edge([(960, 884), (960, 918)])
    body += rect(80, 922, 1760, 112, OUTPUT, "#1f2526", 10, 1.5)
    body += text(108, 986, "交付", 22, OUTPUT, 700)
    for i, (t, d) in enumerate(DELIVER):
        cx = 220 + i * 404
        body += rect(cx, 940, 384, 76, "#444", "#2d2d2d", 8)
        body += text(cx + 18, 970, t, 18, FG, 700) + text(cx + 18, 1000, d, 15, NOTE, limit=330)
    body += link("../../作业要求/大作业1_要求存档.md",
                 text(1840, 1062, "数值为给定假设下的程序结果，输入见报告第 3、7 节　·　要求原文：作业要求/大作业1_要求存档.md　·　交付 REQ-07～11",
                      13, NOTE, anchor="end"))
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
