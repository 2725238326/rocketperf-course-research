"""Shared SVG primitives for the report/PPT figures.

Hierarchy comes from three levels: tinted zone panels, white cards with a
coloured header band, and body text with **bold** key values. ``limit`` (px)
raises instead of letting text overflow its box.
"""
from html import escape

INK = "#16212e"; BODY = "#3a4654"; MUTED = "#6e7a88"; HAIR = "#d5dbe3"; STROKE = "#55606e"
NAVY = "#1f3a5f"; TEAL = "#1d6f6a"; OCHRE = "#a8641a"; SLATE = "#4a5868"
ZONE = {"navy": "#eef2f7", "teal": "#ecf4f3", "ochre": "#f8f1e7", "slate": "#f2f4f6"}
TONE = {"navy": NAVY, "teal": TEAL, "ochre": OCHRE, "slate": SLATE}
FONT = "'Noto Sans SC','Source Han Sans SC','Microsoft YaHei',sans-serif"
MONO = "'Cascadia Mono',Consolas,monospace"
FULL = set("，。：；、（）《》“”·～")


def measure(value, size, mono=False, weight=400):
    value = value.replace("**", "")
    if mono:
        return len(value) * size * 0.6
    width = 0.0
    for c in value:
        code = ord(c)
        width += size if code >= 0x2E80 or c in FULL else size * 0.9 if code >= 0x2000 else size * 0.56
    return width * (1.04 if weight >= 600 else 1.0)


def text(x, y, value, size=18, color=BODY, weight=400, anchor="start", mono=False, limit=None, strong=INK):
    """``**...**`` segments render bold in ``strong`` colour."""
    if limit is not None and measure(value, size, mono, weight) > limit:
        raise ValueError(f"Text overflows {limit}px at {size}px: {value}")
    family = f' font-family="{MONO}"' if mono else ""
    parts = value.split("**")
    inner = "".join(escape(p) if i % 2 == 0 else f'<tspan font-weight="700" fill="{strong}">{escape(p)}</tspan>'
                    for i, p in enumerate(parts) if p)
    return (f'<text x="{x}" y="{y}" font-size="{size}" fill="{color}" font-weight="{weight}" '
            f'text-anchor="{anchor}"{family}>{inner}</text>')


def rect(x, y, w, h, fill="#ffffff", stroke=HAIR, radius=6, dashed=False, width=1.2):
    dash = ' stroke-dasharray="6 4"' if dashed else ""
    return (f'<rect x="{x}" y="{y}" width="{w}" height="{h}" rx="{radius}" fill="{fill}" '
            f'stroke="{stroke}" stroke-width="{width}"{dash}/>')


def line(x1, y1, x2, y2, color=HAIR, width=1):
    return f'<line x1="{x1}" y1="{y1}" x2="{x2}" y2="{y2}" stroke="{color}" stroke-width="{width}"/>'


def arrow(points, dashed=False, color=STROKE, width=1.6):
    dash = ' stroke-dasharray="6 4"' if dashed else ""
    p = " ".join(f"{x},{y}" for x, y in points)
    return (f'<polyline points="{p}" fill="none" stroke="{color}" stroke-width="{width}" '
            f'stroke-linejoin="round" marker-end="url(#ARROW)"{dash}/>')


def link(target, content):
    return f'<a href="{escape(target, quote=True)}">{content}</a>'


def zone(x, y, w, h, tone, label=None):
    """Tinted background panel with a small coloured label at top-left."""
    out = rect(x, y, w, h, ZONE[tone], "none", 10)
    if label:
        out += text(x + 20, y + 32, label, 15, TONE[tone], 700, limit=w - 40)
    return out


def card(x, y, w, h, tone, heading, rows=(), size=17, gap=28, band=40, note=None, dashed=False):
    """White card with a filled header band; rows may contain **bold** values."""
    colour = TONE[tone]
    out = rect(x, y, w, h, "#ffffff", colour if dashed else HAIR, 6, dashed, 1.4 if dashed else 1.2)
    out += (f'<path d="M{x},{y + 6} a6,6 0 0 1 6,-6 h{w - 12} a6,6 0 0 1 6,6 v{band - 6} h-{w} Z" '
            f'fill="{colour}"/>')
    out += text(x + 18, y + band / 2 + 7, heading, 18, "#ffffff", 700, limit=w - 36 - (measure(note, 13) + 12 if note else 0))
    if note:
        out += text(x + w - 16, y + band / 2 + 6, note, 13, "#dfe7ef", 400, anchor="end", mono=True)
    for i, row in enumerate(rows):
        out += text(x + 18, y + band + 32 + i * gap, row, size, BODY, limit=w - 36)
    return out


def header(title, subtitle, width):
    return (f'<rect x="80" y="44" width="6" height="42" fill="{NAVY}"/>'
            + text(102, 78, title, 32, INK, 700)
            + text(102, 114, subtitle, 18, MUTED, limit=width - 182))


def legend(x, y, items):
    """items: (tone, label, dashed)"""
    out = ""
    for tone, label, dashed in items:
        out += rect(x, y - 13, 26, 16, ZONE[tone] if not dashed else "#ffffff", TONE[tone], 3, dashed, 1.4)
        out += text(x + 36, y, label, 15, BODY)
        x += 36 + measure(label, 15) + 32
    return out


def document(prefix, width, height, name, desc, body):
    defs = (f'<marker id="{prefix}-arrow" markerWidth="10" markerHeight="9" refX="9" refY="4.5" '
            f'orient="auto" markerUnits="userSpaceOnUse"><path d="M0,0 L10,4.5 L0,9 Z" fill="{STROKE}"/></marker>')
    body = body.replace("url(#ARROW)", f"url(#{prefix}-arrow)")
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
            f'viewBox="0 0 {width} {height}" role="img" aria-labelledby="{prefix}-title {prefix}-desc">'
            f'<title id="{prefix}-title">{escape(name)}</title><desc id="{prefix}-desc">{escape(desc)}</desc>'
            f'<defs>{defs}</defs><g font-family="{FONT}">'
            f'<rect width="{width}" height="{height}" fill="#ffffff"/>' + body + "</g></svg>\n")
