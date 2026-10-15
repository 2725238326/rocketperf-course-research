"""Program flowchart (GB/T 1526 symbols): entry → compute → cycle → output, independent entries at right."""
from pathlib import Path

from diagram_style import (BG, COMPUTE, CYCLE, FAIL, FG, INPUT, NOTE, OUTPUT, SMALL, VERIFY, band, chip,
                          connector, decision, document, dot, edge, header, io, legend_edge, line, predefined,
                          process, rect, terminator, text)

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'docs/architecture/report-flow.svg'
W, H = 1360, 1020
BUS = 1070                      # right-hand merge bus between main area and the side panel
E_ROW, C_ROW, Y_ROW, OK_ROW, NG_ROW = 165, 380, 630, 800, 885
SIDE = ["run", "nozzle regime", "cycle prescribed", "study area-ratio-ambient",
        "study propellants", "study prescribed-cycle", "thermo · liquid-feed"]


def entry():
    y = E_ROW
    out = band(60, 104, 980, 140, "入口层", INPUT, "src/cli · src/adapters")
    out += terminator(130, y, 100, 40, "开始", stroke=INPUT)
    out += io(340, y, 170, 48, "读入", "命令行 · 交互菜单 · INI", INPUT)
    out += process(575, y, 150, 48, "解析与检查", "单位 · 范围 · 模型 ID", INPUT)
    out += decision(780, y, 110, 64, "输入合法?", stroke=INPUT)
    out += decision(965, y, 110, 64, "命令?", stroke=INPUT)
    out += edge([(180, y), (261, y)]) + edge([(419, y), (500, y)]) + edge([(650, y), (725, y)])
    out += edge([(835, y), (910, y)]) + chip(872, y - 10, "是")
    out += edge([(780, 197), (780, 214)], "fail") + connector(780, 225, "E") + chip(798, 206, "否", FAIL)
    # combustion drops into the compute layer; cycle adiabatic runs down the left margin to the pump
    out += edge([(965, 197), (965, 267), (145, 267), (145, 352)]) + chip(330, 267, "combustion", mono=True)
    out += edge([(145, 267), (40, 267), (40, Y_ROW), (80, Y_ROW)]) + dot(145, 267)
    out += f'<g transform="rotate(-90 40 450)">{chip(40, 450, "cycle adiabatic", mono=True)}</g>'
    out += edge([(1020, y), (1100, y)], "sub") + chip(1060, y - 12, "其他命令")
    return out


def compute():
    y = C_ROW
    out = band(60, 290, 980, 180, "计算层", COMPUTE, "thermo → nozzle · 单室推力")
    out += process(145, y, 130, 56, "入口焓与元素", "NASA9 · 液相表", COMPUTE)
    out += predefined(357, y, 130, 56, "HP 绝热平衡", "九气相 Newton", COMPUTE)
    out += decision(556, y, 104, 72, "收敛且", "a_C ≤ 1?", COMPUTE)
    out += process(762, y, 144, 56, "冻结喷管", "喉部声速 → 面积比", COMPUTE)
    out += decision(968, y, 104, 72, "pa ≤ pe?", stroke=COMPUTE)
    out += edge([(210, y), (292, y)]) + chip(251, y - 12, "h·C/H/O", mono=True)
    out += edge([(422, y), (504, y)]) + chip(463, y - 12, "Tc·p·x", mono=True)
    out += edge([(608, y), (690, y)]) + chip(649, y - 12, "是")
    out += edge([(834, y), (916, y)]) + chip(875, y - 12, "pe", mono=True)
    out += edge([(1020, y), (BUS, y)], head=False) + chip(1045, y - 12, "是")
    for x, why in ((556, "否"), (968, "pa>pe")):
        out += edge([(x, 416), (x, 437)], "fail") + connector(x, 448, "E") + chip(x + 24, 427, why, FAIL)
    return out


def cycle():
    y = Y_ROW
    out = band(60, 520, 980, 180, "循环层", CYCLE, "src/cycle · 研究原型，Q = 0")
    out += process(145, y, 130, 56, "泵", "等密度增压", CYCLE)
    out += predefined(357, y, 140, 56, "预燃室 HP", "调用计算层", CYCLE)
    out += process(549, y, 130, 56, "冻结涡轮", "膨胀 → 涡轮功", CYCLE)
    out += decision(741, y, 120, 72, "轴功闭合?", stroke=CYCLE)
    out += predefined(943, y, 150, 56, "主室 HP + 喷管", "混合入口焓与元素", CYCLE)
    out += edge([(210, y), (287, y)]) + chip(248, y - 12, "h·ṁ", mono=True)
    out += edge([(427, y), (484, y)]) + chip(455, y - 12, "Tpb·x", mono=True)
    out += edge([(614, y), (681, y)]) + chip(647, y - 12, "W_t", mono=True)
    out += edge([(801, y), (868, y)]) + chip(834, y - 12, "是")
    out += edge([(1018, y), (BUS, y)], head=False) + dot(BUS, y) + chip(1044, y - 12, "F·Isp", mono=True)
    out += edge([(741, 666), (741, 684), (357, 684), (357, 658)], "loop")
    out += chip(549, 684, "否 · 调整 p_out / 分流比", CYCLE)
    out += edge([(741, 594), (741, 577)], "fail") + connector(741, 566, "E") + chip(766, 585, "越界", FAIL)
    # predefined processes reuse the compute layer instead of a separate solver
    out += edge([(357, 602), (357, 408)], "call") + chip(357, 490, "调用 HP")
    out += edge([(943, 602), (943, 495), (762, 495), (762, 408)], "call") + chip(852, 495, "调用 HP + 喷管")
    return out


def output():
    out = band(60, 730, 980, 220, "输出层", OUTPUT, "src/adapters · stdout / stderr")
    out += io(560, OK_ROW, 180, 48, "写出结果", "stdout · JSON / 中文表格", OUTPUT)
    out += terminator(250, OK_ROW, 150, 40, "结束 · 退出码 0", stroke=OUTPUT)
    # one merge bus: compute exit, independent entries and cycle exit all feed the result writer from above
    out += edge([(BUS, C_ROW), (BUS, 758), (560, 758), (560, OK_ROW - 25)])
    out += chip(815, 758, "Tc·c*·CF·Isp·残差", mono=True)
    out += edge([(476, OK_ROW), (325, OK_ROW)])
    out += edge([(644, OK_ROW), (760, OK_ROW)], "verify")
    out += process(855, OK_ROW, 190, 48, "离线核验", "CEA 对照 · 守恒残差 · 测试", VERIFY, "5 4")
    out += connector(855, NG_ROW, "E")
    out += io(560, NG_ROW, 180, 48, "写诊断", "stderr · 不写结果", FAIL)
    out += terminator(250, NG_ROW, 160, 40, "结束 · 退出码 2/3/4", stroke=FAIL)
    out += edge([(844, NG_ROW), (644, NG_ROW)], "fail") + edge([(476, NG_ROW), (330, NG_ROW)], "fail")
    out += text(80, 935, "退出码：2 用法错误 · 3 文件 / 格式 / 写出错误 · 4 求解失败", SMALL, NOTE)
    return out


def side():
    x0, w = 1100, 230
    out = rect(x0, 104, w, 270, VERIFY, "#241f27", 8, 1.5)
    out += text(x0 + 16, 128, "独立入口", 13, VERIFY, 700)
    out += text(x0 + 16, 146, "不经循环层", SMALL, NOTE)
    out += line(x0 + 16, 156, x0 + w - 16, 156, "#3c3c3c")
    for i, command in enumerate(SIDE):
        out += text(x0 + 16, 182 + i * 28, command, 11, FG, mono=True, limit=w - 32)
    out += edge([(1215, 374), (1215, 470), (BUS, 470)], head=False) + dot(BUS, 470)
    return out


def legend():
    y, out, x = 978, "", 60
    shapes = [('<rect x="{x}" y="{t}" width="26" height="14" rx="7"', "开始 / 结束"),
              ('<rect x="{x}" y="{t}" width="26" height="14" rx="2"', "处理"),
              ('<rect x="{x}" y="{t}" width="26" height="14" rx="1"', "预定义处理"),
              ('<polygon points="{c},{t} {r},{y} {c},{b} {x},{y}"', "判断"),
              ('<polygon points="{x5},{t} {r},{t} {r5},{b} {x},{b}"', "输入 / 输出")]
    for shape, name in shapes:
        out += shape.format(x=x, t=y - 7, c=x + 13, r=x + 26, b=y + 7, y=y, x5=x + 5, r5=x + 21)
        out += f' fill="{BG}" stroke="{NOTE}" stroke-width="1.2"/>' + text(x + 34, y + 4, name, SMALL, NOTE)
        x += 34 + len(name) * 10 + 26
    out += connector(x + 10, y, "E", r=8) + text(x + 24, y + 4, "失败出口", SMALL, NOTE)
    x, y = 60, 1002
    for kind, name in (("main", "数据流"), ("call", "调用"), ("loop", "迭代"),
                       ("verify", "离线核验"), ("fail", "失败路径")):
        out += legend_edge(x, y, kind, name)
        x += 42 + len(name) * 10 + 34
    return out


def main():
    body = header("计算流程图",
                  "读入并检查 → 单室或循环求解 → 成功写出结果；任一判断失败经 E 返回非零退出码",
                  W)
    body += entry() + compute() + cycle() + output() + side() + legend()
    svg = document("flow", W, H, "计算流程图",
                   "GB/T 1526 程序流程图：入口层解析输入后，combustion 进入 HP 平衡与冻结喷管，cycle adiabatic 经泵、预燃室 HP、"
                   "涡轮与轴功闭合迭代后计算主室与喷管；其余命令为独立入口。成功写出 JSON 或中文表格，失败写诊断并返回退出码 2/3/4。",
                   body)
    OUT.write_text(svg, encoding='utf-8', newline='\n')
    print(OUT)


if __name__ == '__main__':
    main()
