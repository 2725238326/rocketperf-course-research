"""Dark business / components / workflow views; layout is fixed, module facts come from modules.json."""
from diagram_style import (BASE, BODY, COMPUTE, CYCLE, FAIL, FG, INPUT, NOTE, OUTPUT, SMALL, VERIFY, band, card, chip,
                          document, dot, edge, header, legend_edge, legend_swatch, line, rect, text)
from projectlib import ROOT


def source_size(module_id):
    """(.c files, hand-written lines) under src/<id>; generated data tables are excluded."""
    files = [p for p in (ROOT / "src" / module_id).glob("*.[ch]") if not p.name.endswith("_generated.h")]
    lines = sum(len(p.read_text(encoding="utf-8").splitlines()) for p in files)
    return sum(p.suffix == ".c" for p in files), lines


def footer(module_id, state):
    count, lines = source_size(module_id)
    label = "研究原型" if state == "prototype" else "已实现"
    return f"{count} 个 .c · 约 {round(lines, -2)} 行 · {label}"


def components(modules):
    m = {x["id"]: x for x in modules}
    ids = ("cli", "adapters", "thermo", "nozzle", "cycle", "core")
    files = sum(source_size(i)[0] for i in ids)
    total = round(sum(source_size(i)[1] for i in ids), -2)
    W, H = 1280, 772
    body = header("模块架构", f"C17 · {files} 个 .c · 约 {total} 行；上层调用下层，计算层与基础层不做文件读写和动态内存分配", W)
    body += band(60, 104, 1160, 168, "入口层", INPUT)
    body += card(84, 132, 520, 124, INPUT, m["cli"]["name"], "src/cli",
                 ["命令分派 · 参数解析 · 交互菜单", "stdout 结果，stderr 诊断，失败非零退出"], footer("cli", m["cli"]["state"]))
    body += card(676, 132, 520, 124, INPUT, m["adapters"]["name"], "src/adapters",
                 ["INI 算例：单位、范围、模型 ID", "JSON / 中文表格；求解成功后才写出"], footer("adapters", m["adapters"]["state"]))
    body += edge([(604, 194), (676, 194)])
    body += edge([(344, 256), (344, 292)], head=False) + edge([(936, 256), (936, 292)], head=False)
    body += line(254, 292, 1034, 292, "#8a8a8a", 1) + dot(344, 292) + dot(936, 292)
    for x in (254, 644, 1034):
        body += edge([(x, 292), (x, 334)])

    body += band(60, 306, 1160, 230, "计算层", COMPUTE)
    body += card(84, 334, 340, 148, COMPUTE, m["thermo"]["name"], "src/thermo",
                 ["NASA9 物性 · 九气相 HP 平衡", "液态 CH₄ / RP-1 入口焓", "a_C > 1 时拒算"], footer("thermo", m["thermo"]["state"]))
    body += card(474, 334, 340, 148, COMPUTE, m["nozzle"]["name"], "src/nozzle",
                 ["理想 / 冻结组分喷管", "喉部阻塞求流量、c*、Isp", "过膨胀只评估，不预测分离"], footer("nozzle", m["nozzle"]["state"]))
    body += card(864, 334, 340, 148, CYCLE, m["cycle"]["name"], "src/cycle",
                 ["泵 · 涡轮轴功平衡", "Q = 0 开式外排 / 富氧补燃", "质量、元素、焓、轴功守恒"], footer("cycle", m["cycle"]["state"]), dash="5 4")
    body += edge([(474, 408), (424, 408)]) + edge([(864, 408), (814, 408)])
    body += edge([(1034, 482), (1034, 512), (254, 512), (254, 482)]) + chip(644, 512, "循环直接调用 HP")

    body += band(60, 576, 1160, 146, "基础层", BASE)
    body += card(84, 604, 1120, 102, BASE, m["core"]["name"], "src/core",
                 ["夹逼求根 · 有限数检查 · 状态码；无 I/O、无堆分配"], footer("core", m["core"]["state"]))
    body += edge([(644, 536), (644, 604)], "call") + chip(644, 570, "全部模块依赖")
    body += edge([(84, 222), (36, 222), (36, 650), (84, 650)], "call")
    body += legend_swatch(84, 748, CYCLE, "研究原型", "5 4") + legend_edge(190, 748, "main", "调用")
    body += legend_edge(290, 748, "call", "公共依赖（入口层同样依赖基础层）")
    return document("components", W, H, "模块架构",
                    "入口层调用热化学、喷管、循环三个计算模块；循环调用喷管与热化学，喷管调用热化学；所有模块共用数值与错误契约。", body)


def business():
    W, H = 1280, 680
    body = header("业务层次", "应用层按用例组合调用领域模型，领域模型共用基础设施；箭头为调用方向", W)
    cols = (84, 472, 860); cw = 336
    body += band(60, 104, 1160, 130, "应用层", INPUT)
    apps = [("单点性能求解", "combustion · cycle", "给定推进剂、室压、面积比求 Isp"),
            ("域评估", "nozzle regime", "判断匹配 / 过膨胀，不预测分离"),
            ("参数研究", "study", "面积比 × 背压扫描，推进剂成对比较")]
    for x, (title, tag, row) in zip(cols, apps):
        body += card(x, 132, cw, 86, INPUT, title, tag, [row])
        body += edge([(x + cw / 2, 218), (x + cw / 2, 252)], head=False) + dot(x + cw / 2, 252)
    body += line(252, 252, 1028, 252, "#8a8a8a", 1)

    body += band(60, 266, 1160, 214, "领域层", COMPUTE)
    domains = [("thermo · 热化学", "燃烧产物是什么气体？", "Tc · 组分 · h", COMPUTE, None),
               ("nozzle · 喷管", "膨胀能产生多少推力？", "流量 · c* · CF · Isp", COMPUTE, None),
               ("cycle · 循环", "泵与涡轮能否自洽？", "分流量 · 整机推力", CYCLE, "5 4")]
    for x, (title, question, out, color, dash) in zip(cols, domains):
        body += edge([(x + cw / 2, 252), (x + cw / 2, 294)])
        body += card(x, 294, cw, 110, color, title, None, [question], "输出 " + out, dash)
    body += edge([(472, 349), (420, 349)]) + edge([(860, 349), (808, 349)])
    body += edge([(1028, 404), (1028, 450), (252, 450), (252, 404)]) + chip(640, 450, "循环直接调用 HP")

    body += band(60, 520, 1160, 120, "基础层", BASE)
    for x, (title, row) in zip(cols, [("数值核心", "求根 · 有限数检查"), ("物性数据", "NASA9 系数 · 液相表"),
                                       ("错误契约", "状态码；失败不写结果")]):
        body += card(x, 548, cw, 76, BASE, title, None, [row])
    body += edge([(1110, 480), (1110, 548)], "call")
    body += legend_edge(84, 662, "main", "调用") + legend_edge(184, 662, "call", "公共依赖")
    return document("business", W, H, "业务层次",
                    "应用层（单点求解、域评估、参数研究）组合调用领域层的热化学、喷管、循环模型；领域层共用数值核心、物性数据与错误契约。", body)


STAGES = [  # (colour, name, two process lines, product, module, failure)
    (INPUT, "用户输入", ["命令行 / 交互菜单", "选择命令与算例"], "INI 算例文件", "cli", "用法错误 → 退出码 2"),
    (INPUT, "INI 解析", ["键名、单位、范围", "模型 ID 校验"], "Pc·O/F·ε·入口态", "adapters", "格式 3 · 越界 4"),
    (COMPUTE, "HP 平衡", ["入口焓与元素守恒", "九气相 Newton"], "Tc · 组分 x", "thermo", "不收敛 / a_C > 1 → 4"),
    (COMPUTE, "喷管计算", ["冻结组分膨胀", "喉部阻塞 → 出口"], "流量·c*·CF·Isp·pe", "nozzle", "pa > pe 越域 → 4"),
    (CYCLE, "循环闭合", ["泵 · 涡轮轴功平衡", "外层迭代调 03/04"], "分流量 · 涡轮出口压", "cycle", "越界 / 不闭合 → 4"),
    (OUTPUT, "结果输出", ["只在成功后写出", "JSON 或中文表格"], "结果 + 守恒残差", "adapters", "写出失败 → 3"),
    (VERIFY, "核验", ["CEA 对照 · 测试", "quality.py 验收"], "核验记录", "tools / tests", "偏差 → 回到 01"),
]


def workflow():
    W, H = 1280, 520
    x0, cw, gap = 120, 140, 26
    body = header("工作流程", "每步的产物、负责模块与失败处理", W)
    for i, (color, name, rows, product, module, fail) in enumerate(STAGES):
        x, cx = x0 + i * (cw + gap), x0 + i * (cw + gap) + cw / 2
        body += rect(x, 130, cw, 104, color, "#2d2d2d", 8, 1.5, "5 4" if color == VERIFY else None)
        body += text(x + 12, 152, f"{i + 1:02d}", SMALL, color, 700, mono=True)
        body += text(x + 36, 153, name, 14, color, 700, limit=cw - 48)
        body += line(x + 12, 164, x + cw - 12, 164, "#3c3c3c")
        for j, row in enumerate(rows):
            body += text(cx, 188 + j * 20, row, 12, FG, anchor="middle", limit=cw - 16)
        for y, value, colour, mono in ((292, product, FG, False), (336, module, NOTE, True), (380, fail, FAIL, False)):
            body += rect(x, y - 18, cw, 32, "#333", "#222", 4)
            body += text(cx, y + 3, value, SMALL if not mono else 11, colour, anchor="middle", mono=mono, limit=cw - 10)
        if i < len(STAGES) - 1:
            body += edge([(x + cw, 182), (x + cw + gap, 182)], "verify" if i == 5 else "main")
    for y, name in ((292, "产物"), (336, "模块"), (380, "失败")):
        body += text(100, y + 4, name, 12, NOTE, 700, anchor="end")
    # combustion has no cycle layer: nozzle output goes straight to the writer
    a, b = x0 + 3 * (cw + gap) + cw / 2, x0 + 5 * (cw + gap) + cw / 2
    body += edge([(a, 130), (a, 112), (b, 112), (b, 130)], "sub") + chip((a + b) / 2, 112, "combustion 跳过循环")
    # verification feedback: unexplained deviation returns to parameters / model
    f, s = x0 + 6 * (cw + gap) + cw / 2, x0 + cw / 2
    body += edge([(f, 396), (f, 430), (s, 430), (s, 396)], "verify")
    body += legend_edge(120, 476, "main", "数据交接") + legend_edge(240, 476, "sub", "跳过")
    body += legend_edge(372, 476, "verify", "核验反馈")
    body += text(560, 480, "退出码：2 用法 · 3 文件 / 写出 · 4 求解失败；失败时不写结果", SMALL, NOTE)
    return document("workflow", W, H, "工作流程",
                    "用户输入、INI 解析、HP 平衡、喷管计算、循环闭合、结果输出、核验七步；每步列出产物、负责模块与失败处理，核验偏差回到输入。", body)
