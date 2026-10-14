/* Stacked composition, bar and categorical strip charts on the same frame. */
function stackChart(api, spec) {
  const A = axes(api, { ...spec, series: [], bands: spec.refusal ? [spec.refusal] : [] });
  let s = A.s, base = spec.xs.map(() => 0);
  for (const b of spec.bands) {
    const top = base.map((v, i) => v + b.vals[i]);
    const up = spec.xs.map((x, i) => `${A.X(x).toFixed(1)},${A.Y(top[i]).toFixed(1)}`);
    const down = spec.xs.map((x, i) => `${A.X(x).toFixed(1)},${A.Y(base[i]).toFixed(1)}`).reverse();
    s += el("polygon", { points: up.concat(down).join(" "), fill: b.color, stroke: "#fff", "stroke-width": 0.8 });
    const i = spec.xs.length - 1, mid = (top[i] + base[i]) / 2;
    if (b.vals[i] > 0.055) s += el("text", { x: A.X(spec.xs[i]) - 6, y: A.Y(mid) + 4, "text-anchor": "end", "font-size": 12, "font-weight": 650, fill: b.ink || "#fff" }, b.name);
    base = top;
  }
  if (spec.mark !== undefined) s += el("line", { x1: A.X(spec.mark), x2: A.X(spec.mark), y1: A.m.t, y2: A.m.t + A.ph, stroke: "#1A2233", "stroke-width": 1.6, "stroke-dasharray": "4 3" });
  if (spec.refusal) {
    const cx = (A.X(spec.refusal.from) + A.X(spec.refusal.to)) / 2;
    s += el("text", { x: cx, y: A.m.t + A.ph / 2 - 8, "text-anchor": "middle", "font-size": 12, fill: "#7A8496" }, "凝聚碳区") +
      el("text", { x: cx, y: A.m.t + A.ph / 2 + 9, "text-anchor": "middle", "font-size": 12, fill: "#7A8496" }, "C 拒算");
  }
  api.content.innerHTML = s;
  api.hit.setAttribute("x", A.m.l); api.hit.setAttribute("y", A.m.t); api.hit.setAttribute("width", A.pw); api.hit.setAttribute("height", A.ph);
  const snap = (px) => spec.xs.reduce((b, x) => (Math.abs(A.X(x) - px) < Math.abs(A.X(b) - px) ? x : b), spec.xs[0]);
  api.svg.classList.add("pickable");
  api.state = {
    move(px, py, e) {
      const x = snap(px), i = spec.xs.indexOf(x);
      api.hover.innerHTML = el("line", { x1: A.X(x), x2: A.X(x), y1: A.m.t, y2: A.m.t + A.ph, stroke: "#1A2233", "stroke-opacity": 0.35 });
      showTip(tipTable(`O/F = ${ofKey(x)}`, spec.bands.map((b) => [`<span style="color:${b.color}">■</span> ${b.name}`, fx(b.vals[i], 4)]).reverse()), e.clientX, e.clientY);
    },
    pick: spec.pick ? (px) => spec.pick(snap(px)) : null,
  };
}

function barChart(api, spec) {
  const top = Math.max(...spec.bars.map((b) => b.v)) * 1.22 || 1;
  const A = axes(api, { x: { domain: [0, spec.bars.length], ticks: [], title: spec.x.title }, y: { ...spec.y, domain: [0, top] } });
  const bw = A.pw / spec.bars.length;
  let s = A.s;
  spec.bars.forEach((b, i) => {
    const x = A.m.l + i * bw + bw * 0.2, w = bw * 0.6, y = A.Y(b.v);
    s += el("rect", { x, y, width: w, height: A.m.t + A.ph - y, rx: 4, fill: b.hi ? "#1F5FBF" : "#A9BFDF" });
    s += el("text", { x: x + w / 2, y: y - 6, "text-anchor": "middle", "font-size": 12, "font-weight": 650, fill: "#1A2233" }, b.text);
    s += el("text", { x: x + w / 2, y: A.m.t + A.ph + 17, "text-anchor": "middle", "font-size": 11.5, fill: "#7A8496" }, b.label);
  });
  api.content.innerHTML = s;
  api.hit.setAttribute("x", A.m.l); api.hit.setAttribute("y", A.m.t); api.hit.setAttribute("width", A.pw); api.hit.setAttribute("height", A.ph);
  api.svg.classList.toggle("pickable", !!spec.pick);
  const index = (px) => clamp(Math.floor((px - A.m.l) / bw), 0, spec.bars.length - 1);
  api.state = {
    move(px, py, e) {
      const i = index(px);
      api.hover.innerHTML = el("rect", { x: A.m.l + i * bw, y: A.m.t, width: bw, height: A.ph, fill: "#1F5FBF", "fill-opacity": 0.06 });
      showTip(spec.tip(i), e.clientX, e.clientY);
    },
    pick: spec.pick ? (px) => spec.pick(index(px)) : null,
  };
}

/* Categorical strip of log10(|diff|/tolerance); one column per group. */
function stripChart(api, spec) {
  const m = { l: 46, r: 12, t: 22, b: 36 }, pw = api.w - m.l - m.r, ph = api.h - m.t - m.b, lo = -6, hi = 0.35;
  const Y = (q) => m.t + ph - ((clamp(q, lo, hi) - lo) / (hi - lo)) * ph, cw = pw / spec.groups.length;
  let s = "";
  for (let e = lo; e <= 0; e++) {
    s += el("line", { x1: m.l, x2: m.l + pw, y1: Y(e), y2: Y(e), stroke: "#EEF1F5" });
    s += el("text", { x: m.l - 7, y: Y(e) + 4, "text-anchor": "end", "font-size": 11.5, fill: "#7A8496" }, pow10Svg(e));
  }
  s += el("rect", { x: m.l, y: m.t, width: pw, height: ph, fill: "none", stroke: "#D3D9E3" });
  s += el("line", { x1: m.l, x2: m.l + pw, y1: Y(0), y2: Y(0), stroke: "#B3261E", "stroke-width": 1.6 });
  s += el("text", { x: m.l + pw - 6, y: Y(0) - 6, "text-anchor": "end", "font-size": 11.5, fill: "#B3261E" }, "容差 = 1");
  s += el("text", { x: m.l, y: 13, "font-size": 11.5, fill: "#485266" }, "|C − CEA| / 容差");
  const dots = [];
  spec.groups.forEach((g, gi) => {
    const cx = m.l + cw * (gi + 0.5);
    g.points.forEach((p, i) => {
      const x = cx + ((i * 0.6180339887) % 1 - 0.5) * cw * 0.6 + (p.fuel === "rp1" ? cw * 0.05 : -cw * 0.05), y = Y(p.lq);
      dots.push({ x, y, p });
      s += el("circle", { cx: x.toFixed(1), cy: y.toFixed(1), r: 2.7, fill: p.fuel === "rp1" ? "#C8741E" : "#0F8A8A", "fill-opacity": 0.55 });
    });
    s += el("text", { x: cx, y: m.t + ph + 17, "text-anchor": "middle", "font-size": 11.5, fill: "#485266" }, `${g.label} (${g.points.length})`);
  });
  api.content.innerHTML = s;
  api.hit.setAttribute("x", m.l); api.hit.setAttribute("y", m.t); api.hit.setAttribute("width", pw); api.hit.setAttribute("height", ph);
  api.state = {
    move(px, py, e) {
      let best = null, bd = 100;
      for (const d of dots) { const dd = (d.x - px) ** 2 + (d.y - py) ** 2; if (dd < bd) { bd = dd; best = d; } }
      if (!best) { api.hover.innerHTML = ""; hideTip(); return; }
      api.hover.innerHTML = el("circle", { cx: best.x, cy: best.y, r: 6, fill: "none", stroke: "#1A2233", "stroke-width": 1.6 });
      showTip(spec.tip(best.p), e.clientX, e.clientY);
    },
    pick: null,
  };
}
