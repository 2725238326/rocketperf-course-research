/* Chart engine. Each chart is drawn at its container's CSS pixel size (no letterboxing)
 * and redrawn on resize; a persistent hit layer gives crosshair, tooltip and pick. */
const SVGNS = "http://www.w3.org/2000/svg";
function plotFrame(body, draw) {
  const svg = document.createElementNS(SVGNS, "svg");
  const content = document.createElementNS(SVGNS, "g"), hover = document.createElementNS(SVGNS, "g");
  const hit = document.createElementNS(SVGNS, "rect");
  hit.setAttribute("fill", "transparent");
  svg.append(content, hover, hit); body.append(svg);
  const api = { svg, content, hover, hit, w: 0, h: 0, state: null, draw, dragging: false,
    redraw() { if (api.w > 10 && api.h > 10) { api.hover.innerHTML = ""; api.draw(api); } } };
  new ResizeObserver(() => {
    const r = body.getBoundingClientRect(), w = Math.floor(r.width), hh = Math.floor(r.height);
    if (w === api.w && hh === api.h) return;
    api.w = w; api.h = hh; svg.setAttribute("viewBox", `0 0 ${w} ${hh}`); api.redraw();
  }).observe(body);
  const local = (e) => { const r = svg.getBoundingClientRect(); return [e.clientX - r.left, e.clientY - r.top]; };
  svg.addEventListener("pointermove", (e) => {
    const s = api.state; if (!s) return;
    const [x, y] = local(e); s.move(x, y, e);
    if (api.dragging && s.pick) s.pick(x, y);
  });
  svg.addEventListener("pointerleave", () => { api.hover.innerHTML = ""; hideTip(); });
  svg.addEventListener("pointerdown", (e) => {
    const s = api.state; if (!s || !s.pick) return;
    const [x, y] = local(e); api.dragging = true; svg.setPointerCapture(e.pointerId); s.pick(x, y);
  });
  const stop = () => { api.dragging = false; };
  svg.addEventListener("pointerup", stop); svg.addEventListener("pointercancel", stop);
  return api;
}
/* Chart labels may use <sub>/<sup> like HTML; SVG needs tspans. */
const svgText = (t) => String(t).replace(/<sub>(.*?)<\/sub>/g, '<tspan baseline-shift="sub" font-size="0.75em">$1</tspan>')
  .replace(/<sup>(.*?)<\/sup>/g, '<tspan baseline-shift="super" font-size="0.75em">$1</tspan>');
const el = (tag, attrs, text) => {
  if (tag === "text" && text !== undefined) text = svgText(text);
  let s = `<${tag}`;
  for (const k in attrs) if (attrs[k] !== undefined && attrs[k] !== null) s += ` ${k}="${attrs[k]}"`;
  return text === undefined ? `${s}/>` : `${s}>${text}</${tag}>`;
};

function niceTicks(lo, hi, n) {
  const span = hi - lo || 1, raw = span / n, mag = 10 ** Math.floor(Math.log10(raw));
  const step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= raw);
  const out = [];
  for (let v = Math.ceil(lo / step - 1e-9) * step; v <= hi + step * 1e-9; v += step) out.push(+v.toFixed(10));
  return out;
}
function padDomain(lo, hi, f = 0.08) { const d = hi - lo || Math.abs(hi) || 1; return [lo - d * f, hi + d * f]; }
const pow10Svg = (e) => (e === 0 ? "1" : `10<tspan dy="-0.5em" font-size="0.75em">${e < 0 ? "−" : ""}${Math.abs(e)}</tspan>`);
const textWidth = (s) => [...String(s).replace(/<[^>]+>/g, "")].reduce((a, c) => a + (c.charCodeAt(0) > 255 ? 12.5 : 7), 0);

/* Shared axis frame. Returns scales and the plot rectangle. */
function axes(api, spec) {
  const fy = spec.y.fmt || ((v) => fx(v, spec.y.d ?? 0));
  const yLog = !!spec.y.log, xLog = !!spec.x.log;
  const ty = yLog ? Math.log10 : (v) => v, tx = xLog ? Math.log : (v) => v;
  const yt = yLog ? Array.from({ length: Math.floor(spec.y.domain[1]) - Math.ceil(spec.y.domain[0]) + 1 }, (_, i) => Math.ceil(spec.y.domain[0]) + i)
    : niceTicks(spec.y.domain[0], spec.y.domain[1], spec.y.n || 5);
  const yLabels = yt.map((t) => (yLog ? pow10Svg(t) : fy(t)));
  const ends = (spec.series || []).filter((s) => s.end && s.pts.length);
  const m = { l: 14 + Math.max(...yLabels.map((s) => textWidth(yLog ? "10-6" : s)), 20), t: 22, b: 36,
    r: 12 + Math.max(0, ...ends.map((s) => textWidth(s.end) + 10)) };
  const pw = Math.max(40, api.w - m.l - m.r), ph = Math.max(40, api.h - m.t - m.b);
  const [x0, x1] = spec.x.domain.map(tx), [y0, y1] = yLog ? spec.y.domain : spec.y.domain.map(ty);
  const X = (v) => m.l + ((tx(v) - x0) / (x1 - x0)) * pw;
  const Y = (v) => m.t + ph - ((ty(v) - y0) / (y1 - y0)) * ph;
  const Yraw = (e) => m.t + ph - ((e - y0) / (y1 - y0)) * ph;
  const invX = (px) => { const t = x0 + ((px - m.l) / pw) * (x1 - x0); return xLog ? Math.exp(t) : t; };
  let s = "";
  for (const b of spec.bands || []) {
    s += el("rect", { x: X(b.from), y: m.t, width: Math.max(0, X(b.to) - X(b.from)), height: ph, fill: b.fill || "#ECEFF4" });
    if (b.label) s += el("text", { x: (X(b.from) + X(b.to)) / 2, y: m.t + (b.mid ? ph / 2 : 16), "text-anchor": "middle", "font-size": 11.5, fill: "#7A8496" }, b.label);
  }
  yt.forEach((t, i) => {
    const y = yLog ? Yraw(t) : Y(t);
    s += el("line", { x1: m.l, x2: m.l + pw, y1: y, y2: y, stroke: "#EEF1F5" });
    s += el("text", { x: m.l - 7, y: y + 4, "text-anchor": "end", "font-size": 11.5, fill: "#7A8496" }, yLabels[i]);
  });
  for (const t of spec.x.ticks) {
    s += el("line", { x1: X(t), x2: X(t), y1: m.t + ph, y2: m.t + ph + 4, stroke: "#B9C2D0" });
    s += el("text", { x: X(t), y: m.t + ph + 17, "text-anchor": "middle", "font-size": 11.5, fill: "#7A8496" }, spec.x.fmt ? spec.x.fmt(t) : t);
  }
  s += el("rect", { x: m.l, y: m.t, width: pw, height: ph, fill: "none", stroke: "#D3D9E3" });
  s += el("text", { x: m.l + pw, y: api.h - 5, "text-anchor": "end", "font-size": 11.5, fill: "#485266" }, spec.x.title);
  s += el("text", { x: m.l, y: 13, "font-size": 11.5, fill: "#485266" }, spec.y.title);
  for (const hl of spec.hlines || []) {
    const y = yLog ? Yraw(Math.log10(hl.y)) : Y(hl.y);
    s += el("line", { x1: m.l, x2: m.l + pw, y1: y, y2: y, stroke: hl.color || "#9AA4B5", "stroke-width": hl.width || 1.3, "stroke-dasharray": hl.dash });
    if (hl.label) s += el("text", { x: m.l + pw - 6, y: y - 5, "text-anchor": "end", "font-size": 11.5, fill: hl.color || "#7A8496" }, hl.label);
  }
  return { m, pw, ph, X, Y: yLog ? (v) => Yraw(Math.log10(v)) : Y, invX, s };
}

function lineChart(api, spec) {
  const A = axes(api, spec);
  let s = A.s;
  for (const v of spec.vlines || []) {
    s += el("line", { x1: A.X(v.x), x2: A.X(v.x), y1: A.m.t, y2: A.m.t + A.ph, stroke: v.color, "stroke-width": v.width || 1.3, "stroke-dasharray": v.dash });
    if (v.label) s += el("text", { x: A.X(v.x) + (v.left ? -5 : 5), y: A.m.t + 13, "text-anchor": v.left ? "end" : "start", "font-size": 11.5, fill: v.color }, v.label);
  }
  const labels = [];
  for (const se of spec.series) {
    if (!se.pts.length) continue;
    const d = se.pts.map((p, i) => `${i ? "L" : "M"}${A.X(p[0]).toFixed(1)},${A.Y(p[1]).toFixed(1)}`).join("");
    s += el("path", { d, fill: "none", stroke: se.color, "stroke-width": se.width || 2.4, "stroke-dasharray": se.dash, "stroke-linejoin": "round", opacity: se.opacity });
    if (se.end) { const p = se.pts[se.pts.length - 1]; labels.push({ y: A.Y(p[1]), x: A.X(p[0]), text: se.end, color: se.color }); }
    if (se.stop) { const p = se.pts[se.pts.length - 1];
      s += el("path", { d: `M${A.X(p[0]) - 5},${A.Y(p[1]) - 5}l10,10m0,-10l-10,10`, stroke: se.color, "stroke-width": 2.2 }); }
  }
  labels.sort((a, b) => a.y - b.y);
  for (let i = 1; i < labels.length; i++) labels[i].y = Math.max(labels[i].y, labels[i - 1].y + 14);
  for (const l of labels) s += el("text", { x: l.x + 7, y: l.y + 4, "font-size": 12, "font-weight": 650, fill: l.color }, l.text);
  for (const mk of spec.marks || []) {
    const x = A.X(mk.x), y = A.Y(mk.y);
    if (mk.kind === "peak") s += el("path", { d: `M${x},${y - 9}l5,-8h-10z`, fill: mk.color });
    else s += el("circle", { cx: x, cy: y, r: mk.r || 5.5, fill: "#fff", stroke: mk.color, "stroke-width": 2.6 });
    if (mk.label) s += el("text", { x, y: y - (mk.kind === "peak" ? 21 : 11), "text-anchor": "middle", "font-size": 11.5, "font-weight": 650, fill: mk.color }, mk.label);
  }
  api.content.innerHTML = s;
  api.hit.setAttribute("x", A.m.l); api.hit.setAttribute("y", A.m.t); api.hit.setAttribute("width", A.pw); api.hit.setAttribute("height", A.ph);
  const xs = [...new Set(spec.series.flatMap((se) => se.pts.map((p) => p[0])))].sort((a, b) => a - b);
  const snap = (px) => xs.reduce((b, x) => (Math.abs(A.X(x) - px) < Math.abs(A.X(b) - px) ? x : b), xs[0]);
  api.svg.classList.toggle("pickable", !!spec.pick);
  api.state = {
    move(px, py, e) {
      if (!xs.length) return;
      const x = snap(px);
      let g = el("line", { x1: A.X(x), x2: A.X(x), y1: A.m.t, y2: A.m.t + A.ph, stroke: "#1A2233", "stroke-opacity": 0.35 });
      const rows = [];
      for (const se of spec.series) {
        const p = se.pts.find((q) => q[0] === x); if (!p || se.noTip) continue;
        g += el("circle", { cx: A.X(x), cy: A.Y(p[1]), r: 4, fill: se.color, stroke: "#fff", "stroke-width": 1.5 });
        rows.push([`<span style="color:${se.color}">●</span> ${se.name || se.end || ""}`, se.fmt ? se.fmt(p[1]) : fx(p[1], 2)]);
      }
      api.hover.innerHTML = g;
      showTip((spec.tip ? spec.tip(x) : "") + tipTable(`${spec.x.name || spec.x.title} = ${spec.x.fmtTip ? spec.x.fmtTip(x) : x}`, rows), e.clientX, e.clientY);
    },
    pick: spec.pick ? (px) => spec.pick(snap(px)) : null,
  };
}
