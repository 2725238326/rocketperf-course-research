/* Tab: one liquid CH4 chamber, varying nozzle area ratio and back pressure. */
function nozzleSketch(ar, pe, pa, refused) {
  const W = 260, H = 250, cx = W / 2, rt = 12, re = rt * Math.sqrt(ar), rc = 34, top = 18, yt = 74, ye = yt + 14 + 10.5 * Math.sqrt(ar);
  const wall = `M${cx - rc},${top}H${cx + rc}V${top + 26}C${cx + rc},${yt - 18} ${cx + rt * 1.1},${yt - 8} ${cx + rt},${yt}` +
    `C${cx + rt * 1.9},${yt + (ye - yt) * 0.25} ${cx + re * 0.96},${ye - (ye - yt) * 0.4} ${cx + re},${ye}H${cx - re}` +
    `C${cx - re * 0.96},${ye - (ye - yt) * 0.4} ${cx - rt * 1.9},${yt + (ye - yt) * 0.25} ${cx - rt},${yt}C${cx - rt * 1.1},${yt - 8} ${cx - rc},${yt - 18} ${cx - rc},${top + 26}Z`;
  let plume = "";
  if (!refused) {
    const ratio = pa > 0 ? pe / pa : 8, spread = clamp(Math.log(ratio + 1) * 0.55, 0.15, 1.3), len = H - ye - 8;
    const w = re * (1 + spread * 0.5), neck = re * (pa > 0 && ratio < 1.6 ? 0.7 : 0.9);
    plume = `<path class="flicker" d="M${cx - re},${ye}C${cx - w},${ye + len * 0.35} ${cx - neck},${ye + len * 0.75} ${cx - neck * 0.6},${ye + len}H${cx + neck * 0.6}C${cx + neck},${ye + len * 0.75} ${cx + w},${ye + len * 0.35} ${cx + re},${ye}Z" fill="url(#g-plume)"/>`;
    if (pa > 0) for (let i = 0; i < 3; i++) { const yy = ye + len * (0.22 + 0.26 * i), ww = re * (0.5 - 0.1 * i);
      plume += el("path", { d: `M${cx},${yy - 10}L${cx + ww},${yy}L${cx},${yy + 10}L${cx - ww},${yy}Z`, fill: "#FFF7E0", opacity: 0.7 - 0.15 * i }); }
  } else {
    plume = el("path", { d: `M${cx - re},${ye + 6}L${cx + re},${H - 12}M${cx + re},${ye + 6}L${cx - re},${H - 12}`, stroke: "#B3261E", "stroke-width": 3, opacity: 0.7 }) +
      el("text", { x: cx, y: H - 2, "text-anchor": "middle", "font-size": 12, fill: "#B3261E", "font-weight": 650 }, "pa > pe · 模型域外");
  }
  return `<svg class="schematic" viewBox="0 0 ${W} ${H}" preserveAspectRatio="xMidYMid meet">${schematicDefs()}${plume}` +
    el("path", { d: wall, fill: "url(#g-copper)", stroke: "#5A3520", "stroke-width": 1.4 }) +
    el("line", { x1: cx - rt, x2: cx + rt, y1: yt, y2: yt, stroke: "#fff", "stroke-dasharray": "3 3" }) +
    el("text", { x: cx + rc + 8, y: top + 20, "font-size": 12, fill: "#485266" }, "燃烧室") +
    el("text", { x: cx + rt + 8, y: yt + 4, "font-size": 12, fill: "#485266" }, "喉部") +
    el("text", { x: cx + re + 6, y: ye - 4, "font-size": 12, fill: "#485266" }, `ε = ${ar}`) + "</svg>";
}

TABS.push({ id: "nozzle", title: "面积比与背压", init() {
  const V = view("nozzle"), P = {};
  const c1 = card(V.rail, "同一燃烧室，换喷管与高度", `<p>液甲烷/液氧，Pc = 10 MPa，A<sub>t</sub> = 0.01 m²。背压高于理想出口压力时，附着求解被 C 拒绝，另由域评估给出匹配面积比。</p>`);
  P.of = slider(c1, { label: `<span class="dot" style="background:var(--ch4)"></span>甲烷 O/F`, values: AX.ch4_of, value: 2.6, fmt: ofKey, color: "var(--ch4)" });
  P.ar = slider(c1, { label: "面积比 A<sub>e</sub>/A<sub>t</sub>", values: AX.area_ratios, value: 40, ticks: [2, 60] });
  P.env = seg(c1, "环境背压", ENV, 101325);
  presets(c1, [["海平面 ε40（拒算）", () => { P.env.set(101325, true); P.ar.set(40); }], ["海平面 ε10", () => { P.env.set(101325, true); P.ar.set(10); }],
    ["真空 ε40", () => { P.env.set(0, true); P.ar.set(40); }], ["50 kPa ε20", () => { P.env.set(50000, true); P.ar.set(20); }]]);
  const sk = card(V.rail, "", `<h3>喷管示意（喉部固定，出口 ∝ √ε）</h3><div style="position:relative;height:13.5rem"></div>`);
  P.sketch = sk.querySelector("div");
  P.ev = evidence(V.rail);
  P.chain = chain(V.stage, "C 调用链");
  const row = kpiRow(V.stage, 4);
  P.k = [kpi(row, "比冲 I<sub>sp</sub>"), kpi(row, "推力 F"), kpi(row, "出口压力 p<sub>e</sub> 与背压"), kpi(row, "该背压的匹配面积比", "pe = pa")];
  const g = figs(V.stage, "1.35fr 1fr");
  const f1 = figure(g, { title: "比冲随面积比（四种背压）", sub: "对数横轴 · 曲线止于 C 拒算处 × · 虚线为当前背压的匹配面积比 · 点击选面积比",
    legend: ENV.map(([pa, n], i) => legendItem(["#0B2A6B", "#3F78C9", "#8AA9D6", "#C2412D"][i], n)).join("") });
  const f2 = figure(g, { title: "真空比冲的边际收益", sub: "相邻区间每 +1 面积比换来的比冲 · 点击区间跳转" });
  P.take = takeaway(V.stage);
  const COLS = { 0: "#0B2A6B", 5000: "#3F78C9", 50000: "#8AA9D6", 101325: "#C2412D" };
  const STEPS = [[5, 10], [10, 20], [20, 40], [40, 60]];
  P.f1 = plotFrame(f1.body, (api) => {
    const of = P.of.get(), pa = P.env.get(), ar = P.ar.get(), m = DATA.matched_area_ratio[`${ofKey(of)}|${pa}`];
    const series = ENV.map(([e, n]) => {
      const pts = []; let stop = false;
      for (const r of AX.area_ratios) { const q = gridPt("ch4", of, r, e); if (ok(q)) pts.push([r, q.isp]); else { stop = true; break; } }
      return { pts, color: COLS[e], width: e === pa ? 3.4 : 1.8, opacity: e === pa ? 1 : 0.75, stop, name: n, fmt: (v) => `${fx(v, 2)} s`, end: stop ? "" : n };
    });
    const ys = series.flatMap((s) => s.pts.map((q) => q[1])), cur = gridPt("ch4", of, ar, pa);
    lineChart(api, { series, pick: (x) => P.ar.set(x),
      marks: ok(cur) ? [{ x: ar, y: cur.isp, color: COLS[pa] }] : [],
      vlines: [{ x: ar, color: "#7A8496", dash: "4 4" }, ...(m && m >= 2 && m <= 60 ? [{ x: m, color: COLS[pa], dash: "2 3", label: `匹配 ${fx(m, 1)}`, left: m > 20 }] : [])],
      x: { log: true, domain: [2, 60], ticks: [2, 3, 5, 10, 20, 40, 60], title: "面积比 Ae/At（对数）", name: "ε" },
      y: { domain: padDomain(Math.min(...ys), Math.max(...ys), 0.05), d: 0, title: "比冲 Isp / s" },
      tip: (x) => { const q = gridPt("ch4", of, x, pa); return ok(q) ? "" : `<b style="color:#F2A0A0">${envName(pa)}：C 拒算（pa &gt; pe）</b><br>`; } });
  });
  P.f2 = plotFrame(f2.body, (api) => {
    const of = P.of.get(), ar = P.ar.get();
    const bars = STEPS.map(([u, w]) => { const a = gridPt("ch4", of, u, 0), b = gridPt("ch4", of, w, 0);
      return { label: `${u}→${w}`, v: (b.isp - a.isp) / (w - u), text: fx((b.isp - a.isp) / (w - u), 2), hi: ar > u && ar <= w, gain: b.isp - a.isp, dA: b.ae - a.ae }; });
    barChart(api, { bars, x: { title: "面积比区间（真空）" }, y: { d: 1, title: "ΔIsp / Δε  (s)" },
      tip: (i) => tipTable(`面积比 ${bars[i].label}`, [["真空比冲增益", `${sgn(bars[i].gain, 2)} s`], ["出口面积增加", `${fx(bars[i].dA, 3)} m²`], ["每 +1 面积比", `${bars[i].text} s`]]),
      pick: (i) => P.ar.set(STEPS[i][1]) });
  });
  function render() {
    const of = P.of.get(), ar = P.ar.get(), pa = P.env.get(), p = gridPt("ch4", of, ar, pa), vac = gridPt("ch4", of, ar, 0), m = pa ? DATA.matched_area_ratio[`${ofKey(of)}|${pa}`] : null;
    if (ok(p)) {
      P.k[0].set({ v: p.isp, d: 2, unit: "s", foot: pa ? `比真空少 <b>${fx(vac.isp - p.isp, 2)} s</b>（(pe − pa)·Ae 项）` : "真空：压力项全额计入" });
      P.k[1].set({ v: p.f / 1e3, d: 2, unit: "kN", foot: `A<sub>e</sub> <b>${fx(p.ae, 3)}</b> m² · 出口 Ma <b>${fx(p.me, 2)}</b>` });
      P.k[2].set({ v: p.pe / 1e3, d: 1, unit: "kPa", foot: pa ? `${badge(p.pe / pa < 1.15 ? "warn" : "ok", p.pe / pa < 1.15 ? "接近匹配" : "欠膨胀")}pe/pa = <b>${fx(p.pe / pa, 2)}</b>` : `${badge("ok", "真空")}附着解有效` });
    } else {
      P.k[0].set({ refused: "C 拒算", foot: `同几何真空 <b>${fx(vac.isp, 2)} s</b>` });
      P.k[1].set({ refused: "C 拒算", foot: "附着求解不输出外推值" });
      P.k[2].set({ v: vac.pe / 1e3, d: 1, unit: "kPa", foot: `${badge("bad", "过膨胀")}pa/pe = <b>${fx(pa / vac.pe, 2)}</b>` });
    }
    P.k[3].set(m ? { v: m, d: 2, unit: "", foot: ar > m ? `当前 ε${ar} 大于匹配值，压力项为负` : `当前 ε${ar} ≤ 匹配值` } : { html: '<div class="v muted">—</div>', foot: "真空无匹配面积比" });
    P.chain.set([{ name: "HP 平衡", val: ok(vac) ? `${vac.d[0]} 次 · ${fx(vac.tc, 0)} K` : "" }, { name: `冻结膨胀到 ε${ar}`, val: `pe ${kpa(vac.pe)} kPa` },
      { name: "背压判据", val: `pa ${kpa(pa)} kPa ${ok(p) ? "≤" : ">"} pe`, state: ok(p) ? "ok" : "bad" },
      ok(p) ? { name: "推力计账", val: `F ${fx(p.f / 1e3, 1)} kN` } : { name: "域评估", val: m ? `匹配 ε ${fx(m, 2)}` : "—", state: "ok" }]);
    P.ev.set(ok(p) ? [["HP 外层 / Newton", `${p.d[0]} / ${p.d[1]}`], ["连续性残差", sci(p.d[4])], ["推力系数 CF", fx(p.cf, 4)], ["c*", `${fx(p.cstar, 1)} m/s`]]
      : [["附着求解", p.status], ["理想 pe", `${kpa(vac.pe)} kPa`], ["匹配面积比", m ? fx(m, 3) : "—"]], ok(p) ? command("ch4", { of: ofKey(of), ar, pa }) : command("regime", { of: ofKey(of), ar, pa }));
    P.sketch.innerHTML = nozzleSketch(ar, ok(p) ? p.pe : vac.pe, pa, !ok(p));
    const s = STEPS.map(([u, w]) => (gridPt("ch4", of, w, 0).isp - gridPt("ch4", of, u, 0).isp) / (w - u));
    P.take.innerHTML = `真空中每 +1 面积比的比冲收益从 10→20 的 <b>${fx(s[1], 2)} s</b> 降到 20→40 的 <b>${fx(s[2], 2)} s</b>（约前段的 ${fx((100 * s[2]) / s[1], 0)}%），出口面积却翻倍。` +
      (pa ? ` 在${envName(pa)}，匹配面积比约 <b>${fx(m, 1)}</b>；更大的喷管被 C 判为过膨胀域外。` : "") +
      ` 本页为液甲烷推力室；报告 7.3/7.4 分别是给定热状态循环和定比热情景，数值不同、趋势一致。`;
    P.f1.redraw(); P.f2.redraw();
  }
  P.of.on(render); P.ar.on(render); P.env.on(render);
  render();
} });
