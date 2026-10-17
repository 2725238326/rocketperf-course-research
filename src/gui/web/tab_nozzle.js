"use strict";
/* Tab: one liquid CH4 chamber, varying nozzle area ratio and back pressure.
 * nozzle_sweep gives the ε × pa grid (ideal values + regime code); nozzle gives the selected point. */
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
    el("text", { x: cx + re + 6, y: ye - 4, "font-size": 12, fill: "#485266" }, `ε = ${fx(ar, ar < 10 ? 1 : 0)}`) + "</svg>";
}

TABS.push({ id: "nozzle", title: "面积比与背压", init() {
  const V = view("nozzle"), P = {};
  const ARS = [2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50, 60], PAS = ENV.map((e) => e[0]);
  const COLS = { 0: "#0B2A6B", 5000: "#3F78C9", 50000: "#8AA9D6", 101325: "#C2412D" };
  const STEPS = [[5, 10], [10, 20], [20, 40], [40, 60]];
  let grid = null, point = null;
  const c1 = card(V.rail, "同一燃烧室，换喷管与高度", `<p>液甲烷/液氧，Pc = 10 MPa，A<sub>t</sub> = 0.01 m²。背压高于理想出口压力时，附着求解被 C 拒绝，另由域评估给出匹配面积比。</p>`);
  P.of = slider(c1, { label: `<span class="dot" style="background:var(--ch4)"></span>甲烷 O/F`, name: "O/F", min: 2.0, max: 4.0, step: 0.01, value: 2.6, ticks: [2, 4], color: "var(--ch4)" });
  P.ar = slider(c1, { label: "面积比 A<sub>e</sub>/A<sub>t</sub>", name: "面积比", min: 2, max: 60, step: 0.5, value: 40, digits: 1, ticks: [2, 60] });
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
    legend: ENV.map(([pa, n]) => legendItem(COLS[pa], n)).join("") });
  const f2 = figure(g, { title: "真空比冲的边际收益", sub: "相邻区间每 +1 面积比换来的比冲 · 点击区间跳转" });
  P.take = takeaway(V.stage);
  /* grid.isp[j][i]: pressure j, ratio i; regime 0 is the attached (pe ≥ pa) domain the fixed-area solver accepts. */
  const at = (key, ar, pa) => { const i = grid.ars.indexOf(ar), j = grid.pas.indexOf(pa); return i < 0 || j < 0 ? NaN : grid[key][j][i]; };
  const attached = (ar, pa) => at("regime", ar, pa) === 0;
  const matched = (pa) => { const j = grid.pas.indexOf(pa); return j < 0 ? NaN : grid.matched_ar[j]; };
  P.f1 = plotFrame(f1.body, (api) => {
    if (!grid) return plotMessage(api, "C 计算中…");
    const pa = P.env.get(), ar = P.ar.get(), m = matched(pa);
    const series = ENV.map(([e, n]) => {
      const pts = []; let stop = false;
      for (const r of ARS) { if (attached(r, e)) pts.push([r, at("isp", r, e)]); else { stop = true; break; } }
      return { pts, color: COLS[e], width: e === pa ? 3.4 : 1.8, opacity: e === pa ? 1 : 0.75, stop, name: n, fmt: (v) => `${fx(v, 2)} s`, end: stop ? "" : n };
    });
    const ys = series.flatMap((s) => s.pts.map((q) => q[1])), cur = point && point.ok && point.result.attached.ok ? point.result.attached : null;
    lineChart(api, { series, pick: (x) => P.ar.set(x),
      marks: cur ? [{ x: ar, y: cur.isp, color: COLS[pa] || "#1F5FBF" }] : [],
      vlines: [{ x: ar, color: "#7A8496", dash: "4 4" }, ...(finite(m) && m >= 2 && m <= 60 ? [{ x: m, color: COLS[pa], dash: "2 3", label: `匹配 ${fx(m, 1)}`, left: m > 20 }] : [])],
      x: { log: true, domain: [2, 60], ticks: [2, 3, 5, 10, 20, 40, 60], title: "面积比 Ae/At（对数）", name: "ε" },
      y: { domain: padDomain(Math.min(...ys), Math.max(...ys), 0.05), d: 0, title: "比冲 Isp / s" },
      tip: (x) => (attached(x, pa) ? "" : `<b style="color:#F2A0A0">${envName(pa)}：C 拒算（pa &gt; pe）</b><br>`) });
  });
  P.f2 = plotFrame(f2.body, (api) => {
    if (!grid) return plotMessage(api, "C 计算中…");
    const ar = P.ar.get(), ae = (r) => r * AT;
    const bars = STEPS.map(([u, w]) => { const gain = at("isp", w, 0) - at("isp", u, 0);
      return { label: `${u}→${w}`, v: gain / (w - u), text: fx(gain / (w - u), 2), hi: ar > u && ar <= w, gain, dA: ae(w) - ae(u) }; });
    barChart(api, { bars, x: { title: "面积比区间（真空）" }, y: { d: 1, title: "ΔIsp / Δε  (s)" },
      tip: (i) => tipTable(`面积比 ${bars[i].label}`, [["真空比冲增益", `${sgn(bars[i].gain, 2)} s`], ["出口面积增加", `${fx(bars[i].dA, 3)} m²`], ["每 +1 面积比", `${bars[i].text} s`]]),
      pick: (i) => P.ar.set(STEPS[i][1]) });
  });
  const runGrid = RP.channel("nozzle_sweep", (e) => { grid = e.ok ? e.result : null; render(); });
  const runPoint = RP.channel("nozzle", (e) => { point = e; render(); });
  const solveGrid = () => runGrid({ fuel: "ch4", pc: PC, of: P.of.get(), at: AT, ars: ARS, pas: PAS });
  const solvePoint = () => runPoint({ fuel: "ch4", pc: PC, of: P.of.get(), ar: P.ar.get(), pa: P.env.get(), at: AT });
  function render() {
    const of = P.of.get(), ar = P.ar.get(), pa = P.env.get();
    if (point && point.ok) {
      const r = point.result, att = r.attached.ok ? r.attached : null, vac = r.vacuum.ok ? r.vacuum : null, pe = r.ideal.exit.gas.p, m = r.regime.matched_ar;
      if (att) {
        P.k[0].set({ v: att.isp, d: 2, unit: "s", foot: pa && vac ? `比真空少 <b>${fx(vac.isp - att.isp, 2)} s</b>（(pe − pa)·Ae 项）` : "真空：压力项全额计入" });
        P.k[1].set({ v: att.thrust / 1e3, d: 2, unit: "kN", foot: `A<sub>e</sub> <b>${fx(att.exit_area, 3)}</b> m² · 出口 Ma <b>${fx(r.ideal.exit.mach, 2)}</b>` });
        P.k[2].set({ v: pe / 1e3, d: 1, unit: "kPa", foot: pa ? `${badge(pe / pa < 1.15 ? "warn" : "ok", pe / pa < 1.15 ? "接近匹配" : "欠膨胀")}pe/pa = <b>${fx(pe / pa, 2)}</b>` : `${badge("ok", "真空")}附着解有效` });
      } else {
        P.k[0].set({ refused: "C 拒算", foot: vac ? `同几何真空 <b>${fx(vac.isp, 2)} s</b>` : "" });
        P.k[1].set({ refused: "C 拒算", foot: "附着求解不输出外推值" });
        P.k[2].set({ v: pe / 1e3, d: 1, unit: "kPa", foot: `${badge("bad", "过膨胀")}pa/pe = <b>${fx(pa / pe, 2)}</b>` });
      }
      P.k[3].set(pa && finite(m) ? { v: m, d: 2, unit: "", foot: ar > m ? `当前 ε${fx(ar, 1)} 大于匹配值，压力项为负` : `当前 ε${fx(ar, 1)} ≤ 匹配值` } : { html: '<div class="v muted">—</div>', foot: "真空无匹配面积比" });
      P.chain.set([{ name: "HP 平衡", val: `${r.chamber.hp_iterations} 次 · ${fx(r.chamber.gas.t, 0)} K` }, { name: `冻结膨胀到 ε${fx(ar, 1)}`, val: `pe ${kpa(pe)} kPa` },
        { name: "背压判据", val: `pa ${kpa(pa)} kPa ${att ? "≤" : ">"} pe`, state: att ? "ok" : "bad" },
        att ? { name: "推力计账", val: `F ${fx(att.thrust / 1e3, 1)} kN` } : { name: "域评估", val: finite(m) ? `匹配 ε ${fx(m, 2)}` : "—" }]);
      P.ev.set(att ? [["HP 外层 / Newton", `${r.chamber.hp_iterations} / ${r.chamber.eq_iterations}`], ["连续性残差", sci(att.continuity_residual)], ["推力系数 C<sub>F</sub>", fx(att.cf, 4)], ["c*", `${fx(r.ideal.cstar, 1)} m/s`]]
        : [["附着求解", r.attached.status], ["理想 pe", `${kpa(pe)} kPa`], ["匹配面积比", finite(m) ? fx(m, 3) : "—"], ["0.4·pa 参考面积比", finite(r.regime.separation_ar) ? fx(r.regime.separation_ar, 2) : "—"]],
        att ? CMD.ch4(of, ar, pa) : CMD.regime(of, ar, pa));
      P.sketch.innerHTML = nozzleSketch(ar, pe, pa, !att);
    } else if (point) {
      P.k.forEach((k) => k.set({ refused: "C 拒算" }));
      P.sketch.innerHTML = failure(point);
    }
    if (grid) {
      const s = STEPS.map(([u, w]) => (at("isp", w, 0) - at("isp", u, 0)) / (w - u)), m = matched(pa);
      P.take.innerHTML = `真空中每 +1 面积比的比冲收益从 10→20 的 <b>${fx(s[1], 2)} s</b> 降到 20→40 的 <b>${fx(s[2], 2)} s</b>（约前段的 ${fx((100 * s[2]) / s[1], 0)}%），出口面积却翻倍。` +
        (pa && finite(m) ? ` 在${envName(pa)}，匹配面积比约 <b>${fx(m, 1)}</b>；更大的喷管被 C 判为过膨胀域外。` : "") +
        " 0.4·pa 只是 Summerfield 型经验分离参考，不预测实际分离位置。";
    }
    P.f1.redraw(); P.f2.redraw();
  }
  P.of.on(() => { solveGrid(); solvePoint(); });
  P.ar.on(solvePoint); P.env.on(() => { solvePoint(); P.f1.redraw(); });
  solveGrid(); solvePoint();
} });
