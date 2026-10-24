"""Work2 target business responsibilities, separate from implemented C modules.

The normal render_architecture entry point generates SVG and Mermaid together.
No implementation state or task status is inferred from these capability boxes.
"""
from diagram_kit import (
    BODY, HAIR, INK, MUTED, NAVY, OCHRE, SLATE, TEAL, ZONE,
    arrow, card, document, line, rect, text,
)


MERMAID = """flowchart LR
  Q[研究问题与课程要求] --> S[场景与模型]
  E[对象与证据] -->|有来源的观察及缺口| S
  S -->|完整输入及模型身份| C[C计算]
  P[事前实验协议] -->|判据与比较设计| V[实验与评估]
  C -->|原始状态、结果与诊断| V
  R[开发侧参考与独立检查] -.-> V
  V -->|有条件的结论| D[图表、报告及四项交付]
  V -.->|发现问题，新增版本| S
"""


def business():
    width, height = 1600, 1050
    xs, w = (64, 592, 1120), 416
    out = text(64, 60, "作业二业务架构", 32, INK, 700)
    out += text(64, 96, "从研究问题到可复核结论 · 目标职责设计，不代表各项能力已实现", 18, MUTED)
    out += line(64, 118, 1536, 118)

    out += rect(64, 144, 1472, 68, ZONE["navy"], "none", 8)
    out += text(88, 173, "业务目标", 17, NAVY, 700)
    out += text(202, 173, "以有来源的输入与明确模型，用 C 计算热力性能，解释差异、可信范围与改进价值。", 19, INK, limit=1300)
    out += text(202, 197, "两型研究关联级段、子型和批次；同一计算引擎同时服务方法基准、条件研究与算法实验。", 16, BODY, limit=1300)

    out += card(xs[0], 260, w, 184, "navy", "01 对象与证据", (
        "对象 / 子型 / 批次 / 工况",
        "原文观察、单位、冲突与未知",
        "输出：可引用的参数与缺口",
    ))
    out += card(xs[1], 260, w, 184, "navy", "02 场景与模型", (
        "研究问题、完整输入与显式假设",
        "物种 / 相态 / 入口 / 膨胀边界",
        "输出：可执行的场景与模型版本",
    ))
    out += card(xs[2], 260, w, 184, "teal", "03 C 计算", (
        "入口、TP / HP、喷管及可选循环",
        "按用例组合；数值策略显式选择",
        "输出：原始结果、状态与诊断",
    ))
    for x, label in ((480, "观察及缺口"), (1008, "输入快照")):
        out += arrow([(x, 352), (x + 112, 352)])
        out += text(x + 56, 332, label, 14, BODY, anchor="middle", limit=108)

    out += rect(64, 480, 944, 54, ZONE["ochre"], "none", 8)
    out += text(84, 513, "事前实验协议：比较类型、工况、参考、判据、失败分母与总成本", 19, OCHRE, 600, limit=904)
    out += arrow([(720, 534), (720, 588)])
    out += arrow([(1504, 444), (1504, 558), (880, 558), (880, 588)])
    out += text(1328, 487, "每次尝试均保留", 16, TEAL, anchor="middle", limit=400)
    out += text(1328, 514, "成功与失败进入同一评估", 16, BODY, anchor="middle", limit=400)

    out += card(xs[0], 588, w, 190, "slate", "参考与独立检查", (
        "固定版本参考、解析关系与残差",
        "参考输出同样需要适用性检查",
        "开发侧使用；生产依赖单独核对",
    ), dashed=True)
    out += card(xs[1], 588, w, 190, "ochre", "04 实验与评估", (
        "准确度、可靠性、成本与适用域",
        "实现误差 / 模型差异 / 输入影响",
        "输出：带条件与证据的评估",
    ))
    out += card(xs[2], 588, w, 190, "teal", "05 结论与交付", (
        "回答问题，说明收益、反例和局限",
        "图表 / 报告 / PPT 与源码 / 程序",
        "输出：可追溯结论与冻结材料",
    ))
    out += arrow([(480, 683), (592, 683)], dashed=True)
    out += text(536, 662, "参考证据", 14, SLATE, anchor="middle", limit=108)
    out += arrow([(1008, 683), (1120, 683)])
    out += text(1064, 662, "有条件结论", 14, TEAL, anchor="middle", limit=108)

    out += text(64, 819, "评估发现问题 → 回到来源、场景或算法，新增版本并保留原运行记录。", 18, BODY, limit=1472)
    out += text(64, 851, "结果接收分别检查：执行与求解状态、物理残差和参考差异、目标对象适用性。", 18, BODY, limit=1472)

    out += rect(64, 888, 1472, 88, ZONE["slate"], HAIR, 8)
    out += text(88, 920, "共同支撑", 18, SLATE, 700)
    out += text(222, 920, "唯一任务登记 · 版本与原件保护 · 统一质量 · 真实分工与知识掌握", 19, INK, limit=1270)
    out += text(222, 951, "场景 / 物理模型 / 数值策略 / 执行配置分别留身份；AI作为候选策略，与传统方法共用接收门槛。", 17, BODY, limit=1270)
    out += text(64, 1018, "边界：离线研究与 Windows C 程序；独立用例可直接求 TP、HP 或喷管，不要求每次都走完整循环。", 16, MUTED, limit=1472)
    return document("work2-business", width, height, "作业二业务架构",
                    "五项目标业务能力：对象证据、场景模型、C计算、实验评估、结论交付。"
                    "协议事前定义，参考在开发侧核验，任务与版本治理共同支撑；并非已实现功能清单。", out)


def expected_outputs():
    return {
        "Work2/docs/business-architecture.svg": business(),
        "Work2/docs/business-architecture.mmd": MERMAID,
    }
