"""Program flowchart: input zone → five command branches through solver stages → result zone."""
from pathlib import Path

from diagram_kit import (BODY, INK, MUTED, NAVY, STROKE, TONE, arrow, card, document, header,
                         legend, line, rect, text, zone)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/architecture/report-flow.svg'
WIDTH, HEIGHT = 1920, 1080
TOP, ROW_H, ROW_GAP = 214, 86, 22
STEP_X0, STEP_W, STEP_GAP = 620, 220, 34
END_X = 1600

# Step tone = what kind of physics it computes.
KIND = {"in": "slate", "turbo": "ochre", "chem": "teal", "noz": "navy"}
BRANCHES = [
    ("理想喷管", "run", [("in", "给定 γ、R、T₀、P₀"), ("noz", "定比热等熵膨胀")]),
    ("推力室", "combustion frozen-*", [("in", "入口焓与元素量"), ("chem", "HP 绝热平衡"), ("noz", "冻结喷管")]),
    ("给定温度循环", "cycle prescribed", [("turbo", "泵功与涡轮功"), ("chem", "TP 平衡 → 所需 Q"), ("noz", "主喷管 + 支路喷管")]),
    ("绝热开式 / 补燃", "cycle adiabatic", [("in", "泵后焓（液体表）"), ("turbo", "轴功平衡 → 支路流量"),
                                     ("chem", "预燃室、主室 HP"), ("noz", "主喷管 + 外排")]),
    ("过膨胀诊断", "nozzle regime", [("in", "给定 γ、R、T₀、P₀"), ("noz", "理想 pe、匹配面积比")]),
]


def step(x, y, kind, label):
    tone = KIND[kind]
    return (rect(x, y + 14, STEP_W, ROW_H - 28, "#ffffff", TONE[tone], 6, width=1.4)
            + f'<rect x="{x}" y="{y + 14}" width="6" height="{ROW_H - 28}" rx="2" fill="{TONE[tone]}"/>'
            + text(x + STEP_W / 2 + 3, y + ROW_H / 2 + 6, label, 17, INK, 500, anchor="middle", limit=STEP_W - 24))


def main():
    body = header("程序流程图", "一次计算：读入并检查输入 → 按命令进入对应求解链 → 成功写出结果，失败只返回退出码", WIDTH)
    rows = [TOP + i * (ROW_H + ROW_GAP) for i in range(len(BRANCHES))]
    bottom = rows[-1] + ROW_H
    mid = (TOP + bottom) / 2

    body += zone(80, TOP - 50, 300, bottom - TOP + 70, "slate", "① 输入")
    body += card(104, mid - 150, 252, 120, "slate", "读入", ["命令行参数", "INI 算例 · 中文菜单"], 16, 26)
    body += arrow([(230, mid - 30), (230, mid + 6)])
    body += card(104, mid + 10, 252, 120, "slate", "检查", ["单位、取值范围、模型 ID", "**不合格即停止**"], 16, 26)

    body += zone(400, TOP - 50, END_X - 400 + 30, bottom - TOP + 70, "navy", "② 按命令选择求解链")
    body += arrow([(356, mid + 70), (404, mid + 70)])
    body += line(420, rows[0] + ROW_H / 2, 420, rows[-1] + ROW_H / 2, STROKE, 1.6)
    body += line(404, mid + 70, 420, mid + 70, STROKE, 1.6)
    for (label, command, steps), y in zip(BRANCHES, rows):
        cy = y + ROW_H / 2
        body += rect(436, y + 10, 166, ROW_H - 20, "#ffffff", "#c3ccd8", 6)
        body += text(452, cy - 4, label, 17, INK, 700, limit=140)
        body += text(452, cy + 20, command, 12, MUTED, mono=True, limit=140)
        body += line(420, cy, 436, cy, STROKE, 1.6)
        body += arrow([(602, cy), (STEP_X0 - 3, cy)])
        x = STEP_X0
        for j, (kind, s) in enumerate(steps):
            body += step(x, y, kind, s)
            x += STEP_W
            if j < len(steps) - 1:
                body += arrow([(x, cy), (x + STEP_GAP - 3, cy)]); x += STEP_GAP
        body += line(x, cy, END_X, cy, "#9aa6b4", 1.4)
    body += line(END_X, rows[0] + ROW_H / 2, END_X, rows[-1] + ROW_H / 2, "#9aa6b4", 1.4)

    body += zone(1650, TOP - 50, 190, bottom - TOP + 70, "teal", "③ 结果")
    body += arrow([(END_X, mid), (1670, mid)])
    body += card(1672, TOP + 10, 150, 150, "teal", "成功", ["JSON", "或中文表格"], 16, 28)
    body += card(1672, bottom - 160, 150, 150, "ochre", "失败", ["退出码 2/3/4", "**不写结果**"], 16, 28)
    body += text(1680, mid + 6, "求解完成？", 16, INK, 700)
    body += arrow([(1747, mid - 16), (1747, TOP + 166)])
    body += arrow([(1747, mid + 14), (1747, bottom - 166)])

    body += legend(400, bottom + 52, [("slate", "入口状态", False), ("ochre", "泵与涡轮", False),
                                       ("teal", "燃烧平衡", False), ("navy", "喷管膨胀", False)])

    y = 820
    body += rect(80, y, 1760, 196, "#f7f9fb", "none", 10)
    body += text(108, y + 44, "关键关系", 16, NAVY, 700)
    for i, f in enumerate(["c* = pc·At / ṁ", "CF = F / (pc·At)", "Isp = F / (ṁ·g0)"]):
        body += (f'<text x="{108 + i * 260}" y="{y + 92}" font-size="23" fill="{INK}" '
                 f'font-family="Cambria Math,Cambria,Times New Roman,serif">{f}</text>')
    body += text(108, y + 138, "ṁ 为喉部阻塞质量流量，pc 为燃烧室压力，At 为喉部面积，g0 = 9.80665 m/s²。", 16, MUTED)
    notes = ["附着喷管遇 pa > pe 返回越域，不自动转入诊断；诊断给理想解和经验参考，不计算分离位置。",
             "给定温度循环输出维持温度所需的热量 Q；绝热循环 Q = 0，由入口焓和元素量求燃温。",
             "退出码 2 = 命令用法错误，3 = 文件或格式错误，4 = 求解失败（含越域、不收敛）。"]
    body += text(960, y + 44, "使用要点", 16, NAVY, 700)
    for i, n in enumerate(notes):
        body += text(960, y + 84 + i * 34, n, 16, BODY, limit=860)
    body += line(940, y + 24, 940, y + 172, "#d5dbe3")
    svg = document("flow", WIDTH, HEIGHT, "程序流程图",
                   "输入经读入与检查后，按命令进入理想喷管、推力室、给定温度循环、绝热开式/补燃循环或过膨胀诊断五条求解链；"
                   "求解成功输出JSON或中文表格，失败返回退出码且不写结果。",
                   body)
    OUT.write_text(svg, encoding='utf-8', newline='\n')
    print(OUT)


if __name__ == '__main__':
    main()
