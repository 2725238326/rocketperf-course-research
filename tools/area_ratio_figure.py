"""Area-ratio trade-off figure for the presentation: two stacked panels.

Panel A: vacuum synthetic Isp vs area ratio (3 computed points).
Panel B: exit area vs area ratio (the cost side).
Data from docs/improvement-analysis.md section 1 (prescribed_cycle baseline).
Static SVG, report/PPT use; regenerating this file refreshes the figure.
"""
from pathlib import Path

# data: area_ratio, vacuum_isp_s, exit_area_m2, isp_loss_at_5kPa_s
POINTS = [
    (10, 302.095, 0.338897, 1.748),
    (20, 315.143, 0.677795, 3.475),
    (40, 325.508, 1.355590, 6.931),
]

S1, S2 = "#2a78d6", "#eb6834"
INK, INK2, GRID = "#0b0b0b", "#52514e", "#e4e4e0"
BG = "#fcfcfb"
W, H = 720, 560
PL, PR, TOP = 92, 70, 56
PANEL_H = 210
GAP = 78

def x_scale(r):
    lo, hi = 8, 42
    return PL + (r - lo) / (hi - lo) * (W - PL - PR)

def y_scale_A(v):
    lo, hi = 298, 330
    return TOP + PANEL_H - (v - lo) / (hi - lo) * PANEL_H

def y_scale_B(v):
    lo, hi = 0.0, 1.5
    return TOP + GAP + PANEL_H + (PANEL_H if False else 0) - (v - lo) / (hi - lo) * PANEL_H

def y_scale_B2():
    base = TOP + GAP + PANEL_H
    return base  # unused helper

# geometry: panel A rows [TOP, TOP+PANEL_H]; panel B rows [TOP+GAP+PANEL_H, TOP+GAP+2*PANEL_H]
def topB():
    return TOP + GAP + PANEL_H

def y_B(v):
    lo, hi = 0.0, 1.5
    return topB() + PANEL_H - (v - lo) / (hi - lo) * PANEL_H

out = []
out.append('<?xml version="1.0" encoding="utf-8"?>')
out.append(f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" font-family="Microsoft YaHei, Arial, sans-serif">')
out.append(f'<rect width="{W}" height="{H}" fill="{BG}"/>')

# titles
out.append(f'<text x="{PL}" y="26" font-size="17" font-weight="bold" fill="{INK}">喷管面积比取舍：比冲收益递减，出口面积代价加速</text>')
out.append(f'<text x="{PL}" y="44" font-size="12" fill="{INK2}">给定热状态扫描（prescribed_cycle，100 kg/s、5 MPa/3300 K，真空）；三个计算点，非连续最优</text>')

# Panel A gridlines + axis
for gv in (300, 310, 320):
    y = y_scale_A(gv)
    out.append(f'<line x1="{PL}" y1="{y:.1f}" x2="{W-PR}" y2="{y:.1f}" stroke="{GRID}" stroke-width="1"/>')
    out.append(f'<text x="{PL-8}" y="{y+4:.1f}" font-size="11" fill="{INK2}" text-anchor="end">{gv}</text>')
out.append(f'<text x="{PL-58}" y="{TOP+PANEL_H/2+4}" font-size="12" fill="{INK2}" transform="rotate(-90 {PL-58} {TOP+PANEL_H/2+4})" text-anchor="middle">真空合成比冲 (s)</text>')

# Panel A series: line + markers + direct labels
xs = [x_scale(r) for r, *_ in POINTS]
ysA = [y_scale_A(v) for _, v, *_ in POINTS]
out.append(f'<polyline points="{",".join(f"{x:.1f},{y:.1f}" for x,y in zip(xs,ysA))}" fill="none" stroke="{S1}" stroke-width="2"/>')
# first point label goes below-right (value is at the low end of the scale)
label_pos = [(14, 16), (-4, -14), (-4, -14)]  # (dx, dy) per point
for (r, isp, _, loss), x, y, (dx, dy) in zip(POINTS, xs, ysA, label_pos):
    out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{S1}" stroke="{BG}" stroke-width="2"/>')
    out.append(f'<text x="{x+dx:.1f}" y="{y+dy:.1f}" font-size="12" font-weight="bold" fill="{INK}" text-anchor="middle">{isp:.1f}</text>')
# panel A title
out.append(f'<text x="{PL}" y="{TOP-6}" font-size="12" font-weight="bold" fill="{INK}">A · 真空比冲</text>')

# Panel B
out.append(f'<text x="{PL}" y="{topB()-6}" font-size="12" font-weight="bold" fill="{INK}">B · 出口面积（代价）</text>')
for gv in (0.5, 1.0):
    y = y_B(gv)
    out.append(f'<line x1="{PL}" y1="{y:.1f}" x2="{W-PR}" y2="{y:.1f}" stroke="{GRID}" stroke-width="1"/>')
    out.append(f'<text x="{PL-8}" y="{y+4:.1f}" font-size="11" fill="{INK2}" text-anchor="end">{gv}</text>')
out.append(f'<text x="{PL-58}" y="{topB()+PANEL_H/2+4}" font-size="12" fill="{INK2}" transform="rotate(-90 {PL-58} {topB()+PANEL_H/2+4})" text-anchor="middle">出口面积 (m²)</text>')

ysB = [y_B(a) for *_, a, _ in [(r, i, a, l) for r, i, a, l in POINTS]]
out.append(f'<polyline points="{",".join(f"{x:.1f},{y:.1f}" for x,y in zip(xs,ysB))}" fill="none" stroke="{S2}" stroke-width="2"/>')
# labels above each point (points rise steeply; below would hit the axis)
for (r, isp, area, loss), x, y in zip(POINTS, xs, ysB):
    out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="5" fill="{S2}" stroke="{BG}" stroke-width="2"/>')
    out.append(f'<text x="{x:.1f}" y="{y-14:.1f}" font-size="12" font-weight="bold" fill="{INK}" text-anchor="middle">{area:.3f}</text>')

# shared x axis (bottom of panel B)
yb = topB() + PANEL_H
out.append(f'<line x1="{PL}" y1="{yb}" x2="{W-PR}" y2="{yb}" stroke="{INK2}" stroke-width="1"/>')
for r, *_ in POINTS:
    x = x_scale(r)
    out.append(f'<line x1="{x:.1f}" y1="{yb}" x2="{x:.1f}" y2="{yb+5}" stroke="{INK2}" stroke-width="1"/>')
    out.append(f'<text x="{x:.1f}" y="{yb+20}" font-size="12" fill="{INK}" text-anchor="middle">{r}</text>')
out.append(f'<text x="{(PL+W-PR)/2:.0f}" y="{yb+40}" font-size="12" fill="{INK2}" text-anchor="middle">面积比 Ae/At</text>')

# annotation: the halving ratio between the two segments (panel A's upper-right white space)
out.append(f'<text x="{W-PR-10}" y="{TOP+16}" font-size="11" fill="{INK2}" text-anchor="end">单位面积比冲收益：10→20 为 38.5 s/m²，20→40 为 15.3 s/m²（腰斩）</text>')

# footer note
out.append(f'<text x="{PL}" y="{H-12}" font-size="11" fill="{INK2}">5 kPa背压下三点比冲损失 1.75 / 3.48 / 6.93 s；长度、质量、冷却、分离未计算。数据：docs/improvement-analysis.md</text>')

out.append('</svg>')
Path("docs/area-ratio-tradeoff.svg").write_text("\n".join(out), encoding="utf-8")
print("written docs/area-ratio-tradeoff.svg")
