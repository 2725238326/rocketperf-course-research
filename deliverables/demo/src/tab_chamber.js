/* Tab: liquid CH4/O2 chamber equilibrium versus O/F, with the graphite-activity boundary. */
TABS.push({ id: "chamber", title: "燃烧室与积碳边界", init() {
  const V = view("chamber"), P = {}, ofs = AX.chamber_of;
  const okOfs = ofs.filter((r) => ok(chamberPt(r))), edge = okOfs[0];
  const peakC = peakOf(okOfs.map((r) => [r, chamberPt(r).cstar])), peakT = peakOf(okOfs.map((r) => [r, chamberPt(r).tc]));
  const peakI = peakOf(okOfs.map((r) => [r, chamberPt(r).isp])), gen = DATA.cycles[0];
  const c1 = card(V.rail, "液甲烷 / 液氧燃烧室", `<p>${DATA.provenance.inlets.ch4}；Pc = 10 MPa，九气相 HP 平衡；c* 与比冲取面积比 10 真空冻结喷管。</p>`);
  P.of = slider(c1, { label: `<span class="dot" style="background:var(--ch4)"></span>氧燃比 O/F`, values: ofs, value: 2.6, fmt: (v) => ofKey(v), color: "var(--ch4)" });
  presets(c1, [["c* 峰值", () => P.of.set(peakC[0])], ["比冲峰值", () => P.of.set(peakI[0])], ["基线 3.4", () => P.of.set(3.4)],
    ["发生器 1.0", () => P.of.set(1.0), "朱雀三号一级开式情景的发生器混合比"], ["凝聚碳区", () => P.of.set(0.8)]]);
  card(V.rail, "凝聚碳判据", `<p>九气相模型里没有固体碳。平衡解给出碳的元素化学势 π<sub>C</sub>，石墨活度 <b>a<sub>C</sub> = exp(π<sub>C</sub> − g°<sub>C(gr)</sub>/RT)</b>。` +
    `a<sub>C</sub> &gt; 1 时固体碳更稳定，九气相态已不是平衡解，C 程序直接拒算，不靠经验划 O/F 下限。</p>` +
    `<p class="muted">核对：Boudouard 平衡 2CO = C(gr) + CO₂ 独立重算一致（对数差 &lt; 10⁻⁶）；归档 CEA 扩展产物中 RP-1 O/F 1.0 析出石墨，对应 a<sub>C</sub> ≈ 3.2。</p>`);
  P.ev = evidence(V.rail);
  P.chain = chain(V.stage, "C 调用链");
  const row = kpiRow(V.stage, 4);
  P.k = [kpi(row, "燃烧室温度 T<sub>c</sub>"), kpi(row, "特征速度 c*"), kpi(row, "石墨活度 a<sub>C</sub>", "判据 ≤ 1"), kpi(row, "真空比冲（ε = 10）")];
  const g = figs(V.stage, "1.25fr 1fr", "1fr 1fr");
  const fComp = figure(g, { title: "平衡产物组成随 O/F", sub: "摩尔分数堆叠 · 灰区为 C 拒算的凝聚碳区 · 点击或拖动选 O/F" });
  fComp.el.style.gridRow = "1 / span 2";
  const fPeak = figure(g, { title: "c* 与 T<sub>c</sub> 的峰值不在同一 O/F", sub: "各自相对峰值的百分比",
    legend: legendItem("var(--ch4)", "c*") + legendItem("#C2412D", "T<sub>c</sub>") + legendItem("#7A8496", "真空比冲") });
  const fAc = figure(g, { title: "石墨活度 a<sub>C</sub>（对数轴）", sub: "a<sub>C</sub> = 1 为判据线 · 虚线段为被拒点（数值取自 C 的拒算信息）" });
  P.take = takeaway(V.stage);
  const BANDS = [["H₂O", [2], "#4C8FD6"], ["CO₂", [4], "#9DB7D8"], ["CO", [3], "#E0904A"], ["H₂", [0], "#F2C879", "#5A3A10"],
    ["CH₄", [5], "#0F8A8A"], ["O₂", [1], "#2F4F8F"], ["H/O/OH", [6, 7, 8], "#C9D1DD", "#485266"]];
  const pick = (x) => P.of.set(x);
  P.comp = plotFrame(fComp.body, (api) => stackChart(api, {
    xs: okOfs, mark: P.of.get(), pick,
    bands: BANDS.map(([name, idx, color, ink]) => ({ name, color, ink, vals: okOfs.map((r) => idx.reduce((a, i) => a + chamberPt(r).x[i], 0)) })),
    x: { domain: [ofs[0], ofs[ofs.length - 1]], ticks: [0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4], title: "氧燃比 O/F（质量）" },
    y: { domain: [0, 1], d: 2, title: "摩尔分数" }, refusal: { from: ofs[0], to: edge } }));
  P.peak = plotFrame(fPeak.body, (api) => {
    const rel = (k, ref) => okOfs.map((r) => [r, (100 * chamberPt(r)[k]) / ref]);
    const cur = chamberPt(P.of.get());
    lineChart(api, { pick,
      series: [{ pts: rel("tc", peakT[1]), color: "#C2412D", name: "T<sub>c</sub>", fmt: (v) => `${fx(v, 1)}%` },
        { pts: rel("isp", peakI[1]), color: "#7A8496", width: 1.8, dash: "5 4", name: "真空比冲", fmt: (v) => `${fx(v, 1)}%` },
        { pts: rel("cstar", peakC[1]), color: "#0F8A8A", name: "c*", fmt: (v) => `${fx(v, 1)}%` }],
      marks: [{ x: peakC[0], y: 100, kind: "peak", color: "#0F8A8A", label: `c* ${ofKey(peakC[0])}` },
        { x: peakT[0], y: 100, kind: "peak", color: "#C2412D", label: `T<sub>c</sub> ${ofKey(peakT[0])}` },
        ...(ok(cur) ? [{ x: P.of.get(), y: (100 * cur.cstar) / peakC[1], color: "#0F8A8A" }] : [])],
      bands: [{ from: ofs[0], to: edge }],
      x: { domain: [ofs[0], ofs[ofs.length - 1]], ticks: [0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4], title: "O/F", name: "O/F", fmtTip: ofKey },
      y: { domain: [30, 104], d: 0, title: "相对峰值 %" },
      tip: (x) => { const p = chamberPt(x); return ok(p) ? `<b>T<sub>c</sub> ${fx(p.tc, 1)} K · c* ${fx(p.cstar, 1)} m/s · I<sub>sp</sub> ${fx(p.isp, 2)} s</b><br>` : ""; } });
  });
  P.ac = plotFrame(fAc.body, (api) => {
    const acc = okOfs.map((r) => [r, chamberPt(r).ac]);
    const ref = ofs.filter((r) => !ok(chamberPt(r)) && chamberPt(r).ac).map((r) => [r, chamberPt(r).ac]);
    const cur = chamberPt(P.of.get());
    lineChart(api, { pick,
      series: [{ pts: ref.concat(acc.slice(0, 1)), color: "#B3261E", dash: "5 4", width: 2.2, name: "被拒点", fmt: (v) => fx(v, 2) },
        { pts: acc, color: "#0F8A8A", name: "a<sub>C</sub>", fmt: (v) => sci(v, 3) }],
      marks: [...(cur.ac ? [{ x: P.of.get(), y: cur.ac, color: ok(cur) ? "#0F8A8A" : "#B3261E" }] : []),
        { x: gen.inputs.preburner_oxidizer_fuel_ratio, y: gen.preburner.ac, r: 4.5, color: "#C8741E", label: `发生器 ${fx(gen.preburner.ac, 3)}` }],
      bands: [{ from: ofs[0], to: edge }],
      hlines: [{ y: 1, color: "#B3261E", label: "a<sub>C</sub> = 1" }],
      x: { domain: [ofs[0], ofs[ofs.length - 1]], ticks: [0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4], title: "O/F", name: "O/F", fmtTip: ofKey },
      y: { log: true, domain: [-6, 1], title: "a<sub>C</sub>" } });
  });
  function render() {
    const of = P.of.get(), p = chamberPt(of);
    if (ok(p)) {
      P.k[0].set({ v: p.tc, d: 1, unit: "K", foot: `M <b>${fx(p.mw, 2)}</b> kg/kmol · γ<sub>冻结</sub> <b>${fx(p.gamma, 3)}</b>` });
      P.k[1].set({ v: p.cstar, d: 1, unit: "m/s", foot: `峰值 <b>${fx(peakC[1], 1)}</b> @ O/F ${ofKey(peakC[0])}` });
      P.k[2].set({ html: `<div class="v">${sci(p.ac, 3)}</div>`, foot: p.ac > 0.1 ? `${badge("warn", "接近边界")}仍为气相平衡解` : `${badge("ok", "气相解有效")}远离凝聚碳` });
      P.k[3].set({ v: p.isp, d: 2, unit: "s", foot: `峰值 <b>${fx(peakI[1], 2)} s</b> @ O/F ${ofKey(peakI[0])}` });
    } else {
      P.k[0].set({ refused: "C 拒算", foot: "固体碳稳定，九气相态不是平衡解" });
      P.k[1].set({ refused: "C 拒算", foot: "不外推" });
      P.k[2].set({ html: `<div class="v" style="color:var(--bad)">${fx(p.ac, 2)}</div>`, foot: `${badge("bad", "a<sub>C</sub> > 1")}固体碳热力学稳定` });
      P.k[3].set({ refused: "C 拒算", foot: "—" });
    }
    const d = ok(p) ? p.d : null;
    P.chain.set([{ name: "液体入口查表", val: ok(p) ? `h = ${fx(p.h / 1e6, 3)} MJ/kg` : "CH₄ 120 K / O₂ 100 K" },
      { name: "HP 平衡", val: ok(p) ? `Illinois ${d[0]} 次 · Newton ${d[1]} 次` : "已收敛", state: "ok" },
      { name: "石墨判据", val: `a<sub>C</sub> = ${ok(p) ? Number(p.ac).toExponential(2) : fx(p.ac, 2)}`, state: ok(p) ? "ok" : "bad" },
      { name: "冻结喷管 ε10", val: ok(p) ? `c* ${fx(p.cstar, 1)}` : "未执行", state: ok(p) ? "ok" : "skip" },
      { name: "结果", val: ok(p) ? `T<sub>c</sub> ${fx(p.tc, 0)} K` : "out_of_domain", state: ok(p) ? "ok" : "bad" }]);
    P.ev.set(ok(p) ? [["HP 外层 / 末次 Newton", `${d[0]} / ${d[1]}`], ["元素守恒最大相对残差", sci(d[2])], ["焓残差", `${sci(d[3])} J/kg`], ["喷管连续性残差", sci(d[4])]]
      : [["状态", p.status], ["石墨活度", fx(p.ac, 3)], ["说明", "求解收敛后被判据拒绝"]], command("ch4", { of: ofKey(of), ar: 10, pa: 0 }));
    P.take.innerHTML = `c* 在 O/F ≈ <b>${ofKey(peakC[0])}</b> 达峰，燃温到 <b>${ofKey(peakT[0])}</b> 才达峰：富燃侧产物摩尔质量更小，c* ∝ √(T/M) 先到顶。` +
      `O/F 降到 <b>${ofKey(edge)}</b> 以下 a<sub>C</sub> 越过 1，C 拒算。朱雀三号一级开式发生器（O/F 1.0、11 MPa）a<sub>C</sub> = <b>${fx(gen.preburner.ac, 3)}</b>，在边界内但余量不大。`;
    P.comp.redraw(); P.peak.redraw(); P.ac.redraw();
  }
  P.of.on(render);
  render();
} });
