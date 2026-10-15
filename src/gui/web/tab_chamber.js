"use strict";
/* Tab: liquid CH4/O2 chamber equilibrium versus O/F, with the graphite-activity boundary.
 * The O/F sweep is one chamber_sweep call; the selected point adds a nozzle call (ε10 vacuum). */
TABS.push({ id: "chamber", title: "燃烧室与积碳边界", init() {
  const V = view("chamber"), P = {}, OF = { lo: 0.5, hi: 4.0, n: 36 };
  let sweep = null, point = null, gen = null;
  const c1 = card(V.rail, "液甲烷 / 液氧燃烧室", `<p>CoolProp 单相表 CH₄ 120 K / O₂ 100 K 入口；九气相 HP 平衡；c* 与比冲取面积比 10 真空冻结喷管。</p>`);
  P.pc = slider(c1, { label: "室压 p<sub>c</sub>", name: "室压", unit: "MPa", min: 2, max: 20, step: 0.5, value: 10, digits: 1, ticks: [2, 20] });
  P.of = slider(c1, { label: `<span class="dot" style="background:var(--ch4)"></span>氧燃比 O/F`, name: "O/F", min: OF.lo, max: OF.hi, step: 0.01, value: 2.6, ticks: [0.5, 4], color: "var(--ch4)" });
  presets(c1, [["c* 峰值", () => sweep && P.of.set(peakC()[0])], ["比冲峰值", () => P.of.set(3.2)], ["基线 3.4", () => P.of.set(3.4)],
    ["发生器 1.0", () => P.of.set(1.0), "朱雀三号一级开式情景的发生器混合比"], ["凝聚碳区 0.8", () => P.of.set(0.8), "演示 C 的显式拒算"]]);
  card(V.rail, "凝聚碳判据", `<p>九气相模型里没有固体碳。平衡解给出碳的元素化学势 π<sub>C</sub>，石墨活度 <b>a<sub>C</sub> = exp(π<sub>C</sub> − g°<sub>C(gr)</sub>/RT)</b>。` +
    `a<sub>C</sub> &gt; 1 时固体碳更稳定，九气相平衡假设失效，程序拒算。</p>` +
    `<p class="muted">核对：Boudouard 平衡 2CO = C(gr) + CO₂ 独立重算一致；归档 CEA 扩展产物中 RP-1 O/F 1.0 析出石墨。</p>`);
  P.ev = evidence(V.rail);
  P.chain = chain(V.stage, "C 调用链");
  const row = kpiRow(V.stage, 4);
  P.k = [kpi(row, "燃烧室温度 T<sub>c</sub>"), kpi(row, "特征速度 c*"), kpi(row, "石墨活度 a<sub>C</sub>", "判据 ≤ 1"), kpi(row, "真空比冲（ε = 10）")];
  const g = figs(V.stage, "1.25fr 1fr", "1fr 1fr");
  const fComp = figure(g, { title: "平衡产物组成随 O/F", sub: "摩尔分数堆叠 · 灰区为 C 拒算的凝聚碳区 · 点击或拖动选 O/F" });
  fComp.el.style.gridRow = "1 / span 2";
  const fPeak = figure(g, { title: "c* 与 T<sub>c</sub> 的峰值不在同一 O/F", sub: "各自相对峰值的百分比",
    legend: legendItem("var(--ch4)", "c*") + legendItem("#C2412D", "T<sub>c</sub>") + legendItem("#7A8496", "M̄（右读，相对峰值）") });
  const fAc = figure(g, { title: "石墨活度 a<sub>C</sub>（对数轴）", sub: "a<sub>C</sub> = 1 为判据线 · 红色虚线为被拒点（数值取自 C 的拒算信息）" });
  P.take = takeaway(V.stage);
  const BANDS = [["H₂O", [2], "#4C8FD6"], ["CO₂", [4], "#9DB7D8"], ["CO", [3], "#E0904A"], ["H₂", [0], "#F2C879", "#5A3A10"],
    ["CH₄", [5], "#0F8A8A"], ["O₂", [1], "#2F4F8F"], ["H/O/OH", [6, 7, 8], "#C9D1DD", "#485266"]];

  const okIdx = () => sweep.of.map((_, i) => i).filter((i) => sweep.status[i] === "ok");
  const okOfs = () => okIdx().map((i) => sweep.of[i]);
  const series = (key) => okIdx().map((i) => [sweep.of[i], sweep[key][i]]);
  const peakC = () => peakOf(series("cstar")), peakT = () => peakOf(series("t"));
  const edge = () => okOfs()[0];
  const acRefused = () => sweep.of.map((x, i) => {
    if (sweep.status[i] === "ok") return null;
    const m = /graphite activity ([\d.eE+-]+)/.exec(sweep.message[i]);
    return m ? [x, +m[1]] : null;
  }).filter(Boolean);
  const nearest = (x) => okIdx().reduce((b, i) => (Math.abs(sweep.of[i] - x) < Math.abs(sweep.of[b] - x) ? i : b), okIdx()[0]);
  const pick = (x) => P.of.set(+x.toFixed(2));
  const OFX = { domain: [OF.lo, OF.hi], ticks: [0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4], title: "氧燃比 O/F（质量）", name: "O/F", fmtTip: (x) => fx(x, 2) };

  P.comp = plotFrame(fComp.body, (api) => {
    if (!sweep) return plotMessage(api, "C 计算中…");
    const idx = okIdx(), xs = idx.map((i) => sweep.of[i]);
    stackChart(api, { xs, mark: P.of.get(), pick,
      bands: BANDS.map(([name, ids, color, ink]) => ({ name, color, ink, vals: idx.map((i) => ids.reduce((a, s) => a + sweep.x[s][i], 0)) })),
      x: OFX, y: { domain: [0, 1], d: 2, title: "摩尔分数" }, refusal: edge() > OF.lo ? { from: OF.lo, to: edge() } : null });
  });
  P.peak = plotFrame(fPeak.body, (api) => {
    if (!sweep) return plotMessage(api, "C 计算中…");
    const pc = peakC(), pt = peakT(), mwMax = Math.max(...series("mw").map((p) => p[1]));
    const rel = (key, ref) => series(key).map(([x, y]) => [x, (100 * y) / ref]);
    const cur = point && point.ok ? point.result : null;
    lineChart(api, { pick,
      series: [{ pts: rel("t", pt[1]), color: "#C2412D", name: "T<sub>c</sub>", fmt: (v) => `${fx(v, 1)}%` },
        { pts: rel("mw", mwMax), color: "#7A8496", width: 1.8, dash: "5 4", name: "M̄", fmt: (v) => `${fx(v, 1)}%` },
        { pts: rel("cstar", pc[1]), color: "#0F8A8A", name: "c*", fmt: (v) => `${fx(v, 1)}%` }],
      marks: [{ x: pc[0], y: 100, kind: "peak", color: "#0F8A8A", label: `c* ${fx(pc[0], 2)}` },
        { x: pt[0], y: 100, kind: "peak", color: "#C2412D", label: `T<sub>c</sub> ${fx(pt[0], 2)}` },
        ...(cur ? [{ x: P.of.get(), y: (100 * cur.ideal.cstar) / pc[1], color: "#0F8A8A" }] : [])],
      bands: edge() > OF.lo ? [{ from: OF.lo, to: edge() }] : [], x: OFX, y: { domain: [30, 104], d: 0, title: "相对峰值 %" },
      tip: (x) => { const i = nearest(x); return `<b>T<sub>c</sub> ${fx(sweep.t[i], 1)} K · c* ${fx(sweep.cstar[i], 1)} m/s · M̄ ${fx(sweep.mw[i], 2)}</b><br>`; } });
  });
  P.ac = plotFrame(fAc.body, (api) => {
    if (!sweep) return plotMessage(api, "C 计算中…");
    const acc = series("graphite_activity").filter((p) => p[1] > 0), ref = acRefused();
    const cur = point && point.result ? point.result.chamber.graphite_activity : null;
    const marks = [];
    if (finite(cur)) marks.push({ x: P.of.get(), y: cur, color: point.ok ? "#0F8A8A" : "#B3261E" });
    else if (point && !point.ok) { const m = /graphite activity ([\d.eE+-]+)/.exec(point.message || ""); if (m) marks.push({ x: P.of.get(), y: +m[1], color: "#B3261E" }); }
    if (gen) marks.push({ x: gen.of, y: gen.ac, r: 4.5, color: "#C8741E", label: `发生器 ${fx(gen.ac, 3)}` });
    lineChart(api, { pick,
      series: [{ pts: ref.concat(acc.slice(0, 1)), color: "#B3261E", dash: "5 4", width: 2.2, name: "被拒点", fmt: (v) => fx(v, 2) },
        { pts: acc, color: "#0F8A8A", name: "a<sub>C</sub>", fmt: (v) => sci(v, 3) }],
      marks, bands: edge() > OF.lo ? [{ from: OF.lo, to: edge() }] : [], hlines: [{ y: 1, color: "#B3261E", label: "a<sub>C</sub> = 1" }],
      x: OFX, y: { log: true, domain: [-6, 1], title: "a<sub>C</sub>" } });
  });

  const runSweep = RP.channel("chamber_sweep", (env) => { sweep = env.ok ? env.result : null; render(); });
  const runPoint = RP.channel("nozzle", (env) => { point = env; render(); });
  function solve() {
    const pc = P.pc.get() * 1e6;
    runSweep({ fuel: "ch4", pc, of_min: OF.lo, of_max: OF.hi, n: OF.n });
    runPoint({ fuel: "ch4", pc, of: P.of.get(), ar: 10, pa: 0, at: AT });
  }
  function render() {
    const of = P.of.get(), r = point && point.ok ? point.result : null, refused = point && !point.ok;
    const vac = r && r.vacuum.ok ? r.vacuum : null;
    if (r) {
      const c = r.chamber, gas = c.gas, pc = sweep ? peakC() : null;
      P.k[0].set({ v: gas.t, d: 1, unit: "K", foot: `M̄ <b>${fx(gas.mw, 2)}</b> kg/kmol · γ<sub>冻结</sub> <b>${fx(gas.gamma, 3)}</b>` });
      P.k[1].set({ v: r.ideal.cstar, d: 1, unit: "m/s", foot: pc ? `峰值 <b>${fx(pc[1], 1)}</b> @ O/F ${fx(pc[0], 2)}` : "" });
      P.k[2].set({ html: `<div class="v">${sci(c.graphite_activity, 3)}</div>`, foot: c.graphite_activity > 0.1 ? `${badge("warn", "接近边界")}仍为气相平衡解` : `${badge("ok", "气相解有效")}远离凝聚碳` });
      P.k[3].set(vac ? { v: vac.isp, d: 2, unit: "s", foot: `C<sub>F</sub> <b>${fx(vac.cf, 4)}</b> · F <b>${fx(vac.thrust / 1e3, 1)}</b> kN` } : { refused: "C 拒算" });
    } else if (refused) {
      const m = /graphite activity ([\d.eE+-]+)/.exec(point.message || "");
      P.k[0].set({ refused: "C 拒算", foot: m ? "固体碳稳定" : esc(STATUS_ZH[point.status] || point.status) });
      P.k[1].set({ refused: "C 拒算" });
      P.k[2].set(m ? { html: `<div class="v" style="color:var(--bad)">${fx(+m[1], 2)}</div>`, foot: `${badge("bad", "a<sub>C</sub> &gt; 1")}固体碳热力学稳定` } : { refused: "—" });
      P.k[3].set({ refused: "C 拒算", foot: "—" });
    }
    if (point) {
      const c = r && r.chamber;
      P.chain.set([{ name: "液体入口查表", val: c ? `h = ${fx(c.mixture_h / 1e6, 3)} MJ/kg` : "CH₄ 120 K / O₂ 100 K" },
        { name: "HP 平衡", val: c ? `Illinois ${c.hp_iterations} 次 · Newton ${c.eq_iterations} 次` : "已收敛" },
        { name: "石墨判据", val: c ? `a<sub>C</sub> = ${Number(c.graphite_activity).toExponential(2)}` : "a<sub>C</sub> &gt; 1", state: c ? "ok" : "bad" },
        { name: "冻结喷管 ε10", val: vac ? `c* ${fx(r.ideal.cstar, 1)}` : "未执行", state: vac ? "ok" : "skip" },
        { name: "结果", val: c ? `T<sub>c</sub> ${fx(c.gas.t, 0)} K` : point.status, state: c ? "ok" : "bad" }]);
      P.ev.set(c ? [["HP 外层 / 末次 Newton", `${c.hp_iterations} / ${c.eq_iterations}`], ["元素守恒最大相对残差", sci(c.element_residual)],
        ["焓残差", `${sci(c.enthalpy_residual)} J/kg`], ["喷管连续性残差", vac ? sci(vac.continuity_residual) : "—"]]
        : [["状态", point.status], ["说明", "求解收敛后被判据拒绝"], ["C 消息", `<span style="font-family:var(--ff);white-space:normal">${esc(point.message)}</span>`]],
        CMD.ch4(of, 10, 0) + (P.pc.get() !== 10 ? `   # 界面室压 ${P.pc.get()} MPa` : ""));
    }
    if (sweep) {
      const pc = peakC(), pt = peakT();
      P.take.innerHTML = `当前采样中 c* 在 O/F ≈ <b>${fx(pc[0], 1)}</b> 达峰，燃温到 <b>${fx(pt[0], 1)}</b> 才达峰。c* 同时受 T、平均摩尔质量 M̄ 与 γ 影响，富燃侧 M̄ 更小，c* 峰因此偏向富燃。` +
        (edge() > OF.lo ? ` O/F 降到 <b>${fx(edge(), 1)}</b> 以下 a<sub>C</sub> 越过 1，C 拒算。` : "") +
        (gen ? ` 朱雀三号一级开式发生器（O/F ${fx(gen.of, 1)}）a<sub>C</sub> = <b>${fx(gen.ac, 3)}</b>，在边界内但余量不大。` : "");
    }
    P.comp.redraw(); P.peak.redraw(); P.ac.redraw();
  }
  P.of.on(() => runPoint({ fuel: "ch4", pc: P.pc.get() * 1e6, of: P.of.get(), ar: 10, pa: 0, at: AT }));
  P.pc.on(solve);
  RP.cached("cycle", { case: "cases/vehicles/zq3_y1_stage1.ini" }).then((e) => {
    if (e.ok) { gen = { of: e.result.inputs.preburner_oxidizer_fuel_ratio, ac: e.result.preburner.graphite_activity }; render(); }
  });
  solve();
} });
