"use strict";
/* Minimal SVG line charts: shared x, left/right y axes, optional log x, rejected-domain
 * bands, vertical markers, point markers and a hover readout across series. */
const Chart = (() => {
  function nice(lo, hi, count = 5) {
    if (!(hi > lo)) { hi = lo + 1; }
    const raw = (hi - lo) / count, mag = 10 ** Math.floor(Math.log10(raw)), f = raw / mag;
    const step = (f < 1.5 ? 1 : f < 3 ? 2 : f < 7 ? 5 : 10) * mag;
    const start = Math.ceil(lo / step - 1e-9) * step, ticks = [];
    for (let v = start; v <= hi + step * 1e-6; v += step) ticks.push(+v.toPrecision(12));
    return { ticks, step };
  }
  function logTicks(lo, hi) {
    const out = [];
    for (let e = Math.floor(Math.log10(lo)); e <= Math.ceil(Math.log10(hi)); e++) {
      for (const m of [1, 2, 5]) { const v = m * 10 ** e; if (v >= lo * 0.999 && v <= hi * 1.001) out.push(v); }
    }
    return out;
  }
  function extent(values, pad, zero) {
    const v = values.filter(finite);
    if (!v.length) return [0, 1];
    let lo = Math.min(...v), hi = Math.max(...v);
    if (zero) { lo = Math.min(lo, 0); hi = Math.max(hi, 0); }
    const span = hi - lo || Math.abs(hi) || 1;
    return [lo - span * pad, hi + span * pad];
  }
  function fmt(v, step) {
    const d = step >= 1 ? 0 : Math.min(4, Math.ceil(-Math.log10(step)));
    return v.toLocaleString("zh-CN", { minimumFractionDigits: d, maximumFractionDigits: d });
  }
  function segments(xs, ys) {
    const out = []; let cur = [];
    xs.forEach((x, i) => { if (finite(ys[i]) && finite(x)) cur.push([x, ys[i]]); else if (cur.length) { out.push(cur); cur = []; } });
    if (cur.length) out.push(cur);
    return out;
  }

  function render(host, spec) {
    const w = host.clientWidth, h = host.clientHeight;
    if (w < 40 || h < 40) return;
    host.innerHTML = "";
    const s = svg("svg", { viewBox: `0 0 ${w} ${h}` }, host);
    const right = spec.y2 ? 56 : 16, m = { l: 58, r: right, t: 24, b: 34 };
    const iw = w - m.l - m.r, ih = h - m.t - m.b;
    const series = spec.series.filter((sr) => sr.x && sr.y);
    const allX = series.flatMap((sr) => sr.x).filter(finite);
    const logX = spec.x.log;
    let [x0, x1] = spec.x.domain || [Math.min(...allX), Math.max(...allX)];
    const yDom = (axis) => {
      const cfg = axis === 2 ? spec.y2 : spec.y;
      if (cfg.domain) return cfg.domain;
      return extent(series.filter((sr) => (sr.axis || 1) === axis).flatMap((sr) => sr.y), cfg.pad ?? 0.08, cfg.zero);
    };
    const [ya0, ya1] = yDom(1), yt = spec.y.integer ? { ticks: Array.from({ length: Math.floor(ya1) - Math.ceil(ya0) + 1 }, (_, i) => Math.ceil(ya0) + i), step: 1 } : nice(ya0, ya1, spec.y.ticks || 5);
    const yLo = Math.min(ya0, yt.ticks[0]), yHi = Math.max(ya1, yt.ticks[yt.ticks.length - 1]);
    let y2t, y2Lo, y2Hi;
    if (spec.y2) { const [a, b] = yDom(2); y2t = nice(a, b, spec.y.ticks || 5); y2Lo = Math.min(a, y2t.ticks[0]); y2Hi = Math.max(b, y2t.ticks[y2t.ticks.length - 1]); }
    const lx = (v) => (logX ? Math.log10(v) : v);
    const X = (v) => m.l + (lx(v) - lx(x0)) / (lx(x1) - lx(x0)) * iw;
    const Y = (v, axis) => axis === 2 ? m.t + (1 - (v - y2Lo) / (y2Hi - y2Lo)) * ih : m.t + (1 - (v - yLo) / (yHi - yLo)) * ih;
    const g = svg("g", { class: "grid" }, s);
    yt.ticks.forEach((t) => svg("line", { x1: m.l, x2: m.l + iw, y1: Y(t, 1), y2: Y(t, 1) }, g));
    (spec.bands || []).forEach((b) => {
      const a = X(clamp(b.from, x0, x1)), c = X(clamp(b.to, x0, x1));
      if (c - a < 0.5) return;
      svg("rect", { class: "band", x: a, y: m.t, width: c - a, height: ih }, s);
      if (b.label && c - a > 34) svg("text", { class: "band-label", x: a + 6, y: m.t + 14 }, s).textContent = b.label;
    });
    const ax = svg("g", { class: "axis" }, s);
    svg("line", { x1: m.l, x2: m.l + iw, y1: m.t + ih, y2: m.t + ih }, ax);
    yt.ticks.forEach((t) => {
      const tx = svg("text", { x: m.l - 8, y: Y(t, 1) + 3.5, "text-anchor": "end" }, ax);
      tx.textContent = (spec.y.format || ((v) => fmt(v, yt.step)))(t);
    });
    if (spec.y2) y2t.ticks.forEach((t) => {
      const tx = svg("text", { x: m.l + iw + 8, y: Y(t, 2) + 3.5 }, ax);
      tx.textContent = (spec.y2.format || ((v) => fmt(v, y2t.step)))(t);
    });
    const xt = logX ? logTicks(x0, x1) : nice(x0, x1, Math.max(3, Math.floor(iw / 80))).ticks;
    const xStep = logX ? 1 : nice(x0, x1, Math.max(3, Math.floor(iw / 80))).step;
    xt.forEach((t) => {
      if (t < x0 - 1e-9 || t > x1 + 1e-9) return;
      svg("line", { x1: X(t), x2: X(t), y1: m.t + ih, y2: m.t + ih + 4 }, ax);
      svg("text", { x: X(t), y: m.t + ih + 17, "text-anchor": "middle" }, ax).textContent = (spec.x.format || ((v) => fmt(v, xStep)))(t);
    });
    svg("text", { class: "title-y", x: m.l + iw, y: h - 3, "text-anchor": "end" }, s).textContent = spec.x.label || "";
    svg("text", { class: "title-y", x: m.l - 50, y: 13 }, s).textContent = spec.y.label || "";
    if (spec.y2) svg("text", { class: "title-y", x: m.l + iw + 52, y: 13, "text-anchor": "end" }, s).textContent = spec.y2.label || "";
    if (spec.zero && yLo < 0 && yHi > 0) svg("line", { class: "zero", x1: m.l, x2: m.l + iw, y1: Y(0, 1), y2: Y(0, 1) }, s);
    (spec.vlines || []).forEach((v) => {
      if (!finite(v.x) || v.x < x0 || v.x > x1) return;
      svg("line", { class: "vline", x1: X(v.x), x2: X(v.x), y1: m.t, y2: m.t + ih, style: v.color ? `stroke:${v.color}` : "" }, s);
      if (v.label) svg("text", { class: "ann", x: X(v.x) + 5, y: (v.bottom ? m.t + ih - 6 : m.t + 12) + (v.dy || 0), style: `fill:${v.color || css("--ink-2")}` }, s).textContent = v.label;
    });
    (spec.hlines || []).forEach((hl) => {
      const axis = hl.axis || 1, lo = axis === 2 ? y2Lo : yLo, hi = axis === 2 ? y2Hi : yHi;
      if (!finite(hl.y) || hl.y < lo || hl.y > hi) return;
      svg("line", { class: "vline", x1: m.l, x2: m.l + iw, y1: Y(hl.y, axis), y2: Y(hl.y, axis), style: hl.color ? `stroke:${hl.color}` : "" }, s);
      if (hl.label) svg("text", { class: "ann", x: m.l + iw - 4, y: Y(hl.y, axis) - 5, "text-anchor": "end", style: `fill:${hl.color || css("--ink-2")}` }, s).textContent = hl.label;
    });
    const clip = `c${Math.random().toString(36).slice(2, 8)}`;
    svg("rect", { x: m.l, y: m.t - 2, width: iw, height: ih + 4 }, svg("clipPath", { id: clip }, svg("defs", null, s)));
    const plot = svg("g", { "clip-path": `url(#${clip})` }, s);
    series.forEach((sr) => {
      const axis = sr.axis || 1;
      segments(sr.x, sr.y).forEach((seg) => {
        const d = seg.map(([x, y], i) => `${i ? "L" : "M"}${X(x).toFixed(1)},${Y(y, axis).toFixed(1)}`).join("");
        if (sr.area) svg("path", { class: "area", d: `${d}L${X(seg[seg.length - 1][0])},${m.t + ih}L${X(seg[0][0])},${m.t + ih}Z`, style: `fill:${sr.color}` }, plot);
        svg("path", { class: `series${sr.dash ? " dash" : ""}`, d, style: `stroke:${sr.color}${sr.width ? `;stroke-width:${sr.width}` : ""}` }, plot);
      });
    });
    (spec.markers || []).forEach((mk) => {
      if (!finite(mk.x) || !finite(mk.y) || mk.x < x0 || mk.x > x1) return;
      const cx = X(mk.x), cy = Y(mk.y, mk.axis || 1);
      svg("circle", { class: "marker", cx, cy, r: mk.r || 5, style: `fill:${mk.color}` }, s);
      if (mk.label) {
        const left = cx > m.l + iw - 120;
        svg("text", { class: "ann", x: cx + (left ? -9 : 9), y: cy + (mk.dy ?? -8), "text-anchor": left ? "end" : "start", style: `fill:${mk.color}` }, s).textContent = mk.label;
      }
    });
    const cursor = svg("line", { class: "cursor", y1: m.t, y2: m.t + ih, visibility: "hidden" }, s);
    const dots = series.filter((sr) => !sr.noTip).map((sr) => svg("circle", { r: 3.5, visibility: "hidden", style: `fill:${sr.color};stroke:var(--panel);stroke-width:1.5` }, s));
    const hit = svg("rect", { x: m.l, y: m.t, width: iw, height: ih, fill: "transparent" }, s);
    const ref = series.find((sr) => !sr.noTip) || series[0];
    hit.addEventListener("mousemove", (ev) => {
      if (!ref) return;
      const r = s.getBoundingClientRect(), px = (ev.clientX - r.left) * (w / r.width);
      let best = 0, bd = Infinity;
      ref.x.forEach((x, i) => { const dd = Math.abs(X(x) - px); if (dd < bd) { bd = dd; best = i; } });
      const xv = ref.x[best];
      cursor.setAttribute("x1", X(xv)); cursor.setAttribute("x2", X(xv)); cursor.setAttribute("visibility", "visible");
      const rows = [];
      series.filter((sr) => !sr.noTip).forEach((sr, k) => {
        const yv = sr.y[best];
        if (finite(yv)) { dots[k].setAttribute("cx", X(xv)); dots[k].setAttribute("cy", Y(yv, sr.axis || 1)); dots[k].setAttribute("visibility", "visible"); }
        else dots[k].setAttribute("visibility", "hidden");
        rows.push([sr.name, finite(yv) ? (sr.format || F.g)(yv) : (sr.rejected || "拒算"), sr.color]);
      });
      showTip(tipTable((spec.x.tip || ((v) => F.g(v)))(xv, best), rows.concat(spec.tipExtra ? spec.tipExtra(best) : [])), ev.clientX, ev.clientY);
    });
    hit.addEventListener("mouseleave", () => { hideTip(); cursor.setAttribute("visibility", "hidden"); dots.forEach((d) => d.setAttribute("visibility", "hidden")); });
  }

  /* Re-renders on resize; returns a setter for new specs. */
  function mount(host) {
    let spec = null, size = "";
    new ResizeObserver(() => {
      const next = `${host.clientWidth}x${host.clientHeight}`;
      if (spec && next !== size) { size = next; render(host, spec); }
    }).observe(host);
    return (next) => { spec = next; size = `${host.clientWidth}x${host.clientHeight}`; render(host, spec); };
  }
  function legend(items) {
    return `<div class="legend">${items.map((it) =>
      `<span><i class="${it.dash ? "d" : ""}" style="${it.dash ? `color:${it.color}` : `background:${it.color}`}"></i>${it.name}</span>`).join("")}</div>`;
  }
  return { mount, legend };
})();
