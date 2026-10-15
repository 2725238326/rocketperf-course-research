"""SVG primitives for all architecture figures, rendered in one light print style.

Layout code names colours by the live-panel palette; ``document`` maps them to the
light palette in one pass, so every figure shares the same colours.

Shapes follow GB/T 1526 (ISO 5807) flowchart symbols. Solid edges carry data,
dashed edges are calls, iteration feedback or offline verification. ``limit``
(px) raises instead of letting text overflow its shape.
"""
from html import escape

from diagram_kit import measure

BG = "#1a1a1a"; CARD = "#2d2d2d"; EDGE = "#444"; FG = "#e0e0e0"; NOTE = "#999"
WIRE = "#8a8a8a"; FAINT = "#5a5a5a"; BAND = "#202020"
INPUT = "#4fc3f7"; COMPUTE = "#ff9800"; CYCLE = "#ffc107"; OUTPUT = "#26c6da"; VERIFY = "#ab47bc"
BASE = "#90a4ae"; FAIL = "#ef5350"
FONT = "'Microsoft YaHei','Noto Sans CJK SC','PingFang SC',sans-serif"
MONO = "'Cascadia Mono',Consolas,'JetBrains Mono',monospace"
TITLE, BODY, SMALL = 16, 12, 10
# kind -> (colour, width, dash)
EDGES = {"main": (WIRE, 2, None), "sub": (WIRE, 1, None), "call": (FAINT, 1, "4 3"),
         "loop": (CYCLE, 1, "5 4"), "verify": (VERIFY, 1, "5 4"), "fail": (FAIL, 1, None)}


def text(x, y, value, size=BODY, color=FG, weight=400, anchor="start", mono=False, limit=None):
    if limit is not None and measure(value, size, mono, weight) > limit:
        raise ValueError(f"Text overflows {limit}px at {size}px: {value}")
    family = f' font-family="{MONO}"' if mono else ""
    bold = f' font-weight="{weight}"' if weight != 400 else ""
    return (f'<text x="{x:g}" y="{y:g}" font-size="{size}" fill="{color}"{bold} '
            f'text-anchor="{anchor}"{family}>{escape(value)}</text>')


def rich(x, y, value, size=BODY, color=FG, strong=FG, weight=400, anchor="start", limit=None):
    """``**...**`` segments render bold in ``strong`` colour."""
    if limit is not None and measure(value, size, weight=weight) > limit:
        raise ValueError(f"Text overflows {limit}px at {size}px: {value}")
    parts = value.split("**")
    inner = "".join(escape(p) if i % 2 == 0 else f'<tspan font-weight="700" fill="{strong}">{escape(p)}</tspan>'
                    for i, p in enumerate(parts) if p)
    bold = f' font-weight="{weight}"' if weight != 400 else ""
    return f'<text x="{x:g}" y="{y:g}" font-size="{size}" fill="{color}"{bold} text-anchor="{anchor}">{inner}</text>'


def label(cx, cy, title, sub=None, width=120, color=FG):
    """One or two centred lines; the first line is the step name."""
    if sub is None:
        return text(cx, cy + 4, title, BODY, color, 600, "middle", limit=width)
    return (text(cx, cy - 3, title, BODY, color, 600, "middle", limit=width)
            + text(cx, cy + 13, sub, SMALL, NOTE, anchor="middle", limit=width))


def rect(x, y, w, h, stroke=EDGE, fill=CARD, radius=6, width=1, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return (f'<rect x="{x:g}" y="{y:g}" width="{w:g}" height="{h:g}" rx="{radius}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{width}"{d}/>')


def line(x1, y1, x2, y2, color=EDGE, width=1, dash=None):
    d = f' stroke-dasharray="{dash}"' if dash else ""
    return f'<line x1="{x1:g}" y1="{y1:g}" x2="{x2:g}" y2="{y2:g}" stroke="{color}" stroke-width="{width}"{d}/>'


# --- GB/T 1526 symbols; (cx, cy) is the centre -------------------------------------------------
def terminator(cx, cy, w, h, title, sub=None, stroke=FG):
    return rect(cx - w / 2, cy - h / 2, w, h, stroke, CARD, h / 2, 1.5) + label(cx, cy, title, sub, w - 20)


def process(cx, cy, w, h, title, sub=None, stroke=EDGE, dash=None):
    return rect(cx - w / 2, cy - h / 2, w, h, stroke, CARD, 4, 1.5, dash) + label(cx, cy, title, sub, w - 16)


def predefined(cx, cy, w, h, title, sub=None, stroke=EDGE):
    """Process with double side bars: a solver defined elsewhere in the chart."""
    x0, x1 = cx - w / 2, cx + w / 2
    return (rect(x0, cy - h / 2, w, h, stroke, CARD, 2, 1.5)
            + line(x0 + 8, cy - h / 2, x0 + 8, cy + h / 2, stroke, 1)
            + line(x1 - 8, cy - h / 2, x1 - 8, cy + h / 2, stroke, 1)
            + label(cx, cy, title, sub, w - 28))


def io(cx, cy, w, h, title, sub=None, stroke=EDGE):
    s = 12
    pts = f"{cx - w / 2 + s:g},{cy - h / 2:g} {cx + w / 2:g},{cy - h / 2:g} {cx + w / 2 - s:g},{cy + h / 2:g} {cx - w / 2:g},{cy + h / 2:g}"
    return (f'<polygon points="{pts}" fill="{CARD}" stroke="{stroke}" stroke-width="1.5"/>'
            + label(cx, cy, title, sub, w - 2 * s - 12))


def decision(cx, cy, w, h, title, sub=None, stroke=EDGE):
    pts = f"{cx:g},{cy - h / 2:g} {cx + w / 2:g},{cy:g} {cx:g},{cy + h / 2:g} {cx - w / 2:g},{cy:g}"
    return (f'<polygon points="{pts}" fill="{CARD}" stroke="{stroke}" stroke-width="1.5"/>'
            + label(cx, cy, title, sub, w * 0.6))


def connector(cx, cy, mark, color=FAIL, r=11):
    return (f'<circle cx="{cx:g}" cy="{cy:g}" r="{r}" fill="{BG}" stroke="{color}" stroke-width="1.5"/>'
            + text(cx, cy + 4, mark, SMALL, color, 700, "middle"))


def dot(x, y, color=WIRE):
    return f'<circle cx="{x:g}" cy="{y:g}" r="3" fill="{color}"/>'


# --- edges -------------------------------------------------------------------------------------
def edge(points, kind="main", head=True):
    color, width, dash = EDGES[kind]
    d = f' stroke-dasharray="{dash}"' if dash else ""
    p = " ".join(f"{x:g},{y:g}" for x, y in points)
    end = f' marker-end="url(#ah-{kind})"' if head else ""
    return (f'<polyline points="{p}" fill="none" stroke="{color}" stroke-width="{width}" '
            f'stroke-linejoin="round"{d}{end}/>')


def chip(cx, cy, value, color=NOTE, mono=False, limit=None):
    """Edge label on a background plate so it never sits on a line."""
    w = measure(value, SMALL, mono) + 8
    if limit is not None and w > limit:
        raise ValueError(f"Edge label wider than {limit}px: {value}")
    return (f'<rect x="{cx - w / 2:g}" y="{cy - 7:g}" width="{w:g}" height="14" rx="3" fill="{BG}"/>'
            + text(cx, cy + 3.5, value, SMALL, color, anchor="middle", mono=mono))


# --- layout pieces -----------------------------------------------------------------------------
def band(x, y, w, h, title, color, tag=None):
    """Layer panel: faint fill, coloured layer name at the top-left."""
    out = rect(x, y, w, h, "#333", BAND, 8) + text(x + 14, y + 22, title, 13, color, 700)
    if tag:
        out += text(x + 14 + measure(title, 13, weight=700) + 10, y + 22, tag, SMALL, NOTE, mono=True)
    return out


def card(x, y, w, h, color, title, tag=None, rows=(), footer=None, dash=None):
    """Module card: coloured outline and title, body rows, optional footer note."""
    out = rect(x, y, w, h, color, CARD, 8, 1.5, dash)
    out += text(x + 16, y + 28, title, TITLE, color, 700, limit=w - 32 - (measure(tag, SMALL, True) + 12 if tag else 0))
    if tag:
        out += text(x + w - 14, y + 27, tag, SMALL, NOTE, anchor="end", mono=True)
    out += line(x + 16, y + 40, x + w - 16, y + 40, "#3c3c3c")
    for i, row in enumerate(rows):
        out += text(x + 16, y + 62 + i * 21, row, BODY, FG, limit=w - 32)
    if footer:
        out += text(x + 16, y + h - 14, footer, SMALL, NOTE, limit=w - 32)
    return out


def header(title, subtitle, width):
    return (text(40, 46, title, 22, FG, 700)
            + text(40, 70, subtitle, BODY, NOTE, limit=width - 80)
            + line(40, 86, width - 40, 86, "#333"))


def legend_edge(x, y, kind, value):
    return edge([(x, y), (x + 34, y)], kind) + text(x + 42, y + 4, value, SMALL, NOTE)


def legend_swatch(x, y, color, value, dash=None):
    return rect(x, y - 7, 18, 12, color, CARD, 3, 1.5, dash) + text(x + 26, y + 3, value, SMALL, NOTE)


# Light paper palette. Accents are darkened so text keeps contrast on white.
LIGHT = {"#1a1a1a": "#ffffff", "#2d2d2d": "#ffffff", "#202020": "#f6f7f9", "#222": "#f6f7f9",
         "#241f27": "#f8f2fb", "#1f2526": "#eef8f9", "#333": "#e1e4e8", "#3c3c3c": "#e5e7eb",
         "#444": "#c5cad3", "#e0e0e0": "#1f2328", "#999": "#5f6670", "#8a8a8a": "#6b7280",
         "#5a5a5a": "#9aa1ab", INPUT: "#0277bd", COMPUTE: "#d35400", CYCLE: "#a06d00",
         OUTPUT: "#00838f", VERIFY: "#7b1fa2", BASE: "#546e7a", FAIL: "#c62828"}


def light(svg):
    """Remap every palette colour in one pass, so no replacement is applied twice."""
    import re
    return re.sub(r"#[0-9a-fA-F]{3,6}(?![0-9a-fA-F])", lambda m: LIGHT.get(m.group(0).lower(), m.group(0)), svg)


def document(prefix, width, height, name, desc, body):
    markers = light("".join(
        f'<marker id="ah-{k}" markerWidth="8" markerHeight="8" refX="7" refY="4" orient="auto" '
        f'markerUnits="userSpaceOnUse"><path d="M0,0 L8,4 L0,8 Z" fill="{c}"/></marker>'
        for k, (c, _, _) in EDGES.items()))
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="{prefix}-title {prefix}-desc">'
            f'<title id="{prefix}-title">{escape(name)}</title><desc id="{prefix}-desc">{escape(desc)}</desc>'
            f'<defs>{markers}</defs><g font-family="{FONT}">'
            f'<rect width="{width}" height="{height}" fill="{LIGHT[BG]}"/>' + light(body) + "</g></svg>\n")
