"""Generate the presentation slide diagram: thrust-chamber calculation pipeline.

16:9 animated SVG (SMIL) for the course talk — shows what the program computes,
not the engineering governance view. Deterministic loop, browser-playable.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
OUT = ROOT / 'docs/architecture/live/slide-flow.svg'

W, H = 1600, 900
BG = '#14181d'; PANEL = '#1a1f26'; EDGE = '#3a4552'
INK = '#e8edf2'; DIM = '#9aa7b4'
CY = '#86e1e6'; GR = '#86e0a2'; BL = '#8fb4f6'; YE = '#e3c07a'; PU = '#b9a2f2'


def esc(t):
    return t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def T(x, y, t, c=INK, s=20, b=0, anchor='start'):
    w = ' font-weight="bold"' if b else ''
    return f'<text x="{x}" y="{y}" font-size="{s}" text-anchor="{anchor}" fill="{c}"{w}>{esc(t)}</text>'


def wire(d, color, packets, period=2.6, tail=True):
    s = f'<path d="{d}" stroke="{color}" stroke-opacity="0.45" stroke-width="2" fill="none"/>'
    for i in range(packets):
        s += (f'<circle r="5" fill="{color}">'
              f'<animateMotion dur="{period}s" begin="{-i * period / packets:.2f}s" repeatCount="indefinite" path="{d}"/></circle>')
    return s


def box(x, y, w, h, color, title, lines, glow_delay=None, glow_dur=13.5):
    s = f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="8" fill="{PANEL}" stroke="{color}" stroke-width="2">'
    if glow_delay is not None:
        s += (f'<animate attributeName="stroke-opacity" values="0.45;1;1;0.45" keyTimes="0;0.08;0.25;0.33" '
              f'dur="{glow_dur}s" begin="{glow_delay}s" repeatCount="indefinite"/>'
              f'<animate attributeName="fill-opacity" values="0.5;0.85;0.85;0.5" keyTimes="0;0.08;0.25;0.33" '
              f'dur="{glow_dur}s" begin="{glow_delay}s" repeatCount="indefinite"/>')
    s += '</rect>'
    s += T(x + 16, y + 34, title, color, 21, 1)
    ly = y + 34
    for size, indent, t, c in lines:
        ly += 30
        s += T(x + 16 + indent, ly, t, c, size)
    return s


def main():
    p = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
         f'font-family="Consolas,\'Courier New\',monospace" font-size="20">',
         f'<rect width="{W}" height="{H}" fill="{BG}"/>',
         '<defs><marker id="a" markerWidth="9" markerHeight="9" refX="8" refY="4.5" orient="auto">'
         f'<path d="M0,0 L9,4.5 L0,9 z" fill="{DIM}"/></marker></defs>']

    # title + disclaimer
    p.append(T(60, 70, '推力室性能计算流水线', INK, 30, 1))
    p.append(T(60, 104, '输入明确假设 → C17 热化学求解 → 性能参数输出', DIM, 18))
    p.append(T(1540, 70, '方法算例 · 非真实型号性能', YE, 17, 0, 'end'))

    # top pipeline row
    y0, bh, bw, pitch = 170, 190, 250, 305
    p.append(box(60, y0, bw, bh, CY, '① 输入参数', [
        (17, 0, 'Pc 室压 · O/F 混合比', INK),
        (17, 0, '入口温度/压力/相态', INK),
        (17, 0, 'At 喉部 · 面积比 · 背压', INK),
        (15, 0, '交互菜单 / .ini算例 / CLI', DIM),
    ]))
    p.append(box(60 + pitch, y0, bw, bh, GR, '② NASA9 物性', [
        (17, 0, '九系数多项式 cp/h/s', INK),
        (17, 0, '分温区 · 九气相产物', INK),
        (15, 0, '气态/液体查表入口', DIM),
    ], glow_delay=0.0))
    p.append(box(60 + 2 * pitch, y0, bw, bh, GR, '③ HP 化学平衡', [
        (17, 0, '元素守恒 + 平衡闭合', INK),
        (17, 0, '→ 绝热温度 T_ad', INK),
        (17, 0, '→ 平衡摩尔分数', INK),
        (15, 0, 'c* = Pc·At/ṁ 特征速度', DIM),
    ], glow_delay=4.5))
    p.append(box(60 + 3 * pitch, y0, bw, bh, GR, '④ 喷管膨胀', [
        (17, 0, '冻结温变 / L0定比热', INK),
        (17, 0, '声速喉部 → 阻塞流量', INK),
        (17, 0, '面积比求出口站 pe·ve', INK),
        (15, 0, '背压>pe 附着域外', DIM),
    ], glow_delay=9.0))
    p.append(box(60 + 4 * pitch, y0, bw, bh, BL, '⑤ 性能计账', [
        (17, 0, 'ṁ 流量 · T 各站温度', INK),
        (17, 0, 'F = ṁ·ve + (pe−pa)·Ae', INK),
        (17, 0, 'Isp 比冲 · c* · 推力系数', INK),
        (15, 0, 'JSON契约 / --text / 归档', DIM),
    ]))

    # horizontal connectors
    for i in range(4):
        x1 = 60 + i * pitch + bw + 4
        x2 = 60 + (i + 1) * pitch - 4
        p.append(wire(f'M{x1} {y0 + 95} L{x2} {y0 + 95}', CY if i == 0 else GR if i < 3 else BL, 2))

    # decision diamond below nozzle box
    dx, dy = 60 + 3 * pitch + bw / 2, 500
    p.append(f'<path d="M{dx} {y0 + bh} L{dx} {dy - 44}" stroke="{YE}" stroke-opacity="0.45" stroke-width="2" fill="none"/>')
    p.append(f'<polygon points="{dx},{dy - 44} {dx + 118},{dy} {dx},{dy + 44} {dx - 118},{dy}" '
             f'fill="{PANEL}" stroke="{YE}" stroke-width="2"/>')
    p.append(T(dx, dy - 4, 'pa ≤ pe ?', YE, 19, 1, 'middle'))
    p.append(T(dx, dy + 22, '附着流假设检查', DIM, 14, 0, 'middle'))

    # yes-branch: up-right to accounting box
    yes = f'M{dx + 118} {dy} C {dx + 220} {dy} {60 + 4 * pitch + 125} {dy - 20} {60 + 4 * pitch + 125} {y0 + bh + 4}'
    p.append(f'<path d="{yes}" stroke="{BL}" stroke-opacity="0.45" stroke-width="2" fill="none" marker-end="url(#a)"/>')
    p.append(f'<circle r="5" fill="{BL}"><animateMotion dur="3.2s" repeatCount="indefinite" path="{yes}"/></circle>')
    p.append(T(dx + 235, dy + 26, '是 → 计账', BL, 16, 1, 'middle'))

    # no-branch: left-down to regime box
    rx, ry, rw, rh = 60 + 1 * pitch, 640, 250, 150
    no = f'M{dx - 118} {dy} C {dx - 320} {dy + 10} {rx + rw + 40} {ry - 40} {rx + rw} {ry + 30}'
    p.append(f'<path d="{no}" stroke="{YE}" stroke-opacity="0.45" stroke-width="2" fill="none" marker-end="url(#a)"/>')
    p.append(f'<circle r="5" fill="{YE}"><animateMotion dur="3.6s" begin="1.1s" repeatCount="indefinite" path="{no}"/></circle>')
    p.append(T(dx - 300, dy + 30, '否 · 过膨胀', YE, 16, 1, 'middle'))

    p.append(box(rx, ry, rw, rh, YE, 'regime 域评估', [
        (17, 0, '理想pe · pa/pe', INK),
        (17, 0, '匹配面积比', INK),
        (17, 0, '0.4pa 经验参考', INK),
        (15, 0, '提示 ≠ 分离预测', YE),
    ]))
    p.append(f'<rect x="{rx}" y="{ry}" width="{rw}" height="{rh}" rx="8" fill="none" stroke="{YE}" '
             f'stroke-width="2" opacity="0.4">'
             f'<animate attributeName="opacity" values="0.15;0.15;0.9;0.15" keyTimes="0;0.72;0.8;1" dur="4.5s" repeatCount="indefinite"/></rect>')

    # bottom-left: outputs / traceability strip
    p.append(box(60, 640, 250 + pitch, 150, DIM, '输出与可追溯', [
        (17, 0, 'stdout JSON · stderr 诊断 · 退出码', INK),
        (17, 0, 'results/ 归档 manifest + 哈希', INK),
        (17, 0, '算例 .ini 可整包复跑', INK),
    ]))

    # cycling stage caption
    stages = [('物性查值 cp/h/s', GR), ('平衡迭代 → T_ad≈3602.8 K', GR),
              ('A40 · pa=101325 Pa → 域外，转评估', YE), ('F≈173.7 kN · Isp≈320.8 s（真空算例）', BL)]
    for i, (t, c) in enumerate(stages):
        vis = ['0'] * 4
        vis[i] = '1'
        vis.append('0')
        p.append(f'<text x="60" y="856" font-size="19" opacity="0">'
                 f'<tspan fill="{DIM}">当前阶段：</tspan><tspan fill="{c}" font-weight="bold">{esc(t)}</tspan>'
                 f'<animate attributeName="opacity" values="{";".join(vis)}" '
                 f'keyTimes="0;0.25;0.5;0.75;1" dur="13.5s" repeatCount="indefinite"/></text>')
    p.append(f'<text x="1540" y="856" font-size="15" text-anchor="end" fill="{DIM}">'
             f'方法独立实现 · 数据为研究算例</text>')
    p.append('</svg>')
    OUT.write_text('\n'.join(p), encoding='utf-8')
    print('wrote', OUT)


if __name__ == '__main__':
    main()
