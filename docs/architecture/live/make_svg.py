"""Render docs/architecture/live/config.json to an animated SVG (SMIL).

Companion to rocketperf-live.html: same geometry, no HTML/JS dependency.
The SVG loops deterministically; open in a browser to see motion.
"""
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
CFG = ROOT / 'docs/architecture/live/config.json'
OUT = ROOT / 'docs/architecture/live/rocketperf-live.svg'

INK = '#e8edf2'; DIM = '#9aa7b4'; BG = '#14181d'; PANEL = '#1a1f26'; EDGE = '#3a4552'


def esc(t):
    return t.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')


def width_of(t, size):
    return sum(size * 1.2 if ord(c) > 0x2E7F else size * 0.6 for c in t)


def main():
    cfg = json.loads(CFG.read_text(encoding='utf-8'))
    W, H = cfg['canvas']['width'], cfg['canvas']['height']
    fs = cfg['theme']['fontSize']
    C = cfg['theme']['colors']
    dur = cfg['canvas']['duration']
    col = dict(fg=INK, dim=DIM, wh='#ffffff', **C)

    parts = [f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" '
             f'font-family="Consolas,\'Courier New\',monospace" font-size="{fs}">',
             f'<rect width="{W}" height="{H}" fill="{BG}"/>']

    def text(x, y, runs, size=fs, anchor='start'):
        s = f'<text x="{x}" y="{y}" font-size="{size}" text-anchor="{anchor}">'
        for t, c, b in runs:
            weight = ' font-weight="bold"' if b else ''
            s += f'<tspan fill="{col[c]}"{weight}>{esc(t)}</tspan>'
        return s + '</text>'

    def box_lines(el):
        """Emit line runs of a box element; returns y cursor."""
        x, y = el['x'], el['y']
        pad = el.get('pad', [0, 0, 0])
        lx, ly = x + pad[2], y + pad[0] + fs
        out = []
        for ln in el.get('lines', []):
            if ln == '' or ln is None:
                ly += cfg['theme']['lineHeight']
                continue
            if isinstance(ln, dict) and ('trigger' in ln or 'items' in ln):
                ly += cfg['theme']['lineHeight']
                continue
            size = ln.get('size', fs) if isinstance(ln, dict) else fs
            indent = ln.get('indent', 0) if isinstance(ln, dict) else 0
            if isinstance(ln, dict) and 'runs' in ln:
                runs = []
                for r in ln['runs']:
                    if isinstance(r, str):
                        runs.append((r, 'fg', 0))
                    elif 'v' in r:
                        runs.append(('{dyn}', r.get('c', 'fg'), r.get('b', 0)))
                    else:
                        runs.append((r.get('t', ''), r.get('c', 'fg'), r.get('b', 0)))
            else:
                t = ln.get('t', '') if isinstance(ln, dict) else str(ln)
                c = ln.get('c', 'fg') if isinstance(ln, dict) else 'fg'
                b = ln.get('b', 0) if isinstance(ln, dict) else 0
                runs = [(t, c, b)]
            for t, c, b in runs:
                if t == '{dyn}':
                    continue
                out.append(text(lx + indent, ly, [(t, c, b)], size=size))
            ly += cfg['theme']['lineHeight']
        return out

    # terminal titlebar
    parts.append(f'<rect x="0" y="0" width="{W}" height="54" fill="{PANEL}"/>')
    for i, dot in enumerate(('#ff5f57', '#febc2e', '#28c840')):
        parts.append(f'<circle cx="{30 + i * 22}" cy="27" r="7" fill="{dot}"/>')
    parts.append(text(W / 2, 33, [(cfg['titlebar']['text'], 'dim', 0)], anchor='middle', size=16))

    # machine-driven visuals collected per element type
    stage_dur = cfg['machines']['stage']['period']
    stage_n = len(cfg['machines']['stage']['order'])
    gate_dur = cfg['machines']['gate']['period']
    gate_on = cfg['machines']['gate']['on']
    gate_t0 = cfg['machines']['gate']['t0']
    gate_items = len(cfg['machines']['gate']['items'])

    for el in cfg['elements']:
        kind = el.get('type')
        if kind == 'text':
            runs = []
            for r in el.get('runs', []):
                if 'sw' in r:
                    runs.append(('■ ', r['sw'], 0))
                elif 'v' in r:
                    runs.append(('—', r.get('c', 'fg'), r.get('b', 0)))
                else:
                    runs.append((r.get('t', ''), r.get('c', 'fg'), r.get('b', 0)))
            x = el.get('x', 0) + (el.get('w', 0) / 2 if el.get('align') == 'center' else 0)
            parts.append(text(x, el['y'], runs,
                              anchor='middle' if el.get('align') == 'center' else 'start'))
        elif kind == 'rule':
            parts.append(f'<line x1="{el["x"]}" y1="{el["y"]}" x2="{el["x"] + el["w"]}" y2="{el["y"]}" stroke="{EDGE}"/>')
        elif kind == 'box':
            glow = el.get('then', {}).get('glow')
            stroke = col.get(el.get('color', 'fg'), INK)
            fill_op, stroke_op = 0.55, 0.9
            rect = (f'<rect x="{el["x"]}" y="{el["y"]}" width="{el["w"]}" height="{el["h"]}" rx="6" '
                    f'fill="{PANEL}" stroke="{stroke}" fill-opacity="{fill_op}" stroke-opacity="{stroke_op}">')
            if glow and 'when' in el:
                idx = int(el['when']['eq'])
                slot = stage_dur
                vals, keys = [], []
                for i in range(stage_n):
                    vals.append('1' if i == idx else '0.35')
                vals.append(vals[0])
                keys = [round(i / stage_n, 4) for i in range(stage_n)] + [1]
                rect += (f'<animate attributeName="stroke-opacity" values="{";".join(map(str, vals))}" '
                         f'keyTimes="{";".join(map(str, keys))}" dur="{stage_dur * stage_n}s" repeatCount="indefinite"/>')
            rect += '</rect>'
            parts.append(rect)
            parts += box_lines(el)
        elif kind == 'path':
            pts = el['points']
            d = 'M' + ' L'.join(f'{x} {y}' for x, y in pts)
            parts.append(f'<path d="{d}" stroke="{col[el["color"]]}" stroke-opacity="0.45" fill="none"/>')
            flow = el.get('flow')
            if flow:
                plen = sum(((b[0] - a[0]) ** 2 + (b[1] - a[1]) ** 2) ** 0.5 for a, b in zip(pts, pts[1:]))
                for off in flow.get('offsets', [0]):
                    parts.append(
                        f'<circle r="5" fill="{col[el["color"]]}">'
                        f'<animateMotion dur="{flow["period"]}s" begin="{-off * flow["period"]}s" repeatCount="indefinite" path="{d}"/>'
                        f'</circle>')
        elif kind == 'tarrow':
            (x1, y1), (x2, y2) = el['from'], el['to']
            i = el['i']
            begin = gate_t0 + i * 0.1
            keys = [0, round((begin) / dur, 4), round((begin + gate_on) / dur, 4), 1]
            parts.append(
                f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{col["pu"]}" stroke-width="2" '
                f'marker-end="url(#arr)">'
                f'<animate attributeName="opacity" values="0.15;0.15;1;0.15" keyTimes="{";".join(map(str, keys))}" '
                f'dur="{gate_dur}s" begin="{(i) * 0.15}s" repeatCount="indefinite"/></line>')
        elif kind == 'log':
            x, y, w, rows = el['x'], el['y'], el['w'], el['rows']
            h = el['padTop'] + el['padBottom'] + rows * cfg['theme']['lineHeight']
            parts.append(f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="6" fill="{PANEL}" stroke="{EDGE}"/>')
            parts.append(text(x + el.get('titleX', 14), y + el['padTop'] + fs,
                              [(el.get('title', 'log'), 'dim', 0)], size=16))
            seqs = [v['m'] for v in cfg['machines']['stage']['values']] + \
                   [m[0] for m in cfg['machines']['pipe']['log']['msgs']] + \
                   [it['name'] + ' · 通过' for it in cfg['machines']['gate']['items']]
            slot = dur / (rows * 3)
            for r in range(rows):
                seq = [seqs[(r + k * rows) % len(seqs)] for k in range(3)]
                for k, msg in enumerate(seq):
                    vis = ['0'] * 9
                    vis[k * 3], vis[k * 3 + 1] = '1', '1'
                    kt = [round(i / 9, 4) for i in range(10)]
                    parts.append(
                        f'<text x="{x + 14}" y="{y + el["padTop"] + (r + 1) * cfg["theme"]["lineHeight"]}" '
                        f'font-size="{fs - 2}" opacity="0"><tspan fill="{DIM}">{esc(msg)}</tspan>'
                        f'<animate attributeName="opacity" values="{";".join(vis)};0" keyTimes="{";".join(map(str, kt))}" '
                        f'dur="{slot * 9}s" repeatCount="indefinite"/></text>')
            parts.append(
                f'<text x="{x + w - 24}" y="{y + h - el["padBottom"]}" fill="{col["cy"]}">▌'
                f'<animate attributeName="opacity" values="1;0;1" dur="1.2s" repeatCount="indefinite"/></text>')

    parts.insert(1, '<defs><marker id="arr" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto">'
                    f'<path d="M0,0 L8,4 L0,8 z" fill="{col["pu"]}"/></marker></defs>')
    parts.append(text(W / 2, cfg['credit']['y'], [(cfg['credit']['text'], 'dim', 0)],
                      anchor='middle', size=14))
    parts.append('</svg>')
    OUT.write_text('\n'.join(parts), encoding='utf-8')
    print('wrote', OUT)


if __name__ == '__main__':
    main()
