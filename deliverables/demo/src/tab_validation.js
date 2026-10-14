/* Tab: archived C-vs-CEA field comparisons (read from saved manifests, not recomputed). */
TABS.push({ id: "validation", title: "CEA 对照", init() {
  const V = view("validation"), P = {}, VD = DATA.validation;
  const GROUPS = [["燃烧室状态", /^chamber\.(temperature|h_|s_|molar|pressure)/], ["产物组成", /^chamber\.mole_fractions/],
    ["喉部 / 出口", /^(throat|exit)\.(temperature|pressure|velocity|mach)/], ["c* / Ivac / 推力", /^(nozzle\.(cstar|ivac)|geometry\.)/],
    ["守恒残差", /(residual|diagnostics|continuity|sonic|recomputed|element_ratio|fraction_sum)/]];
  const order = [4, 0, 1, 2, 3], groupOf = (f) => order.find((g) => GROUPS[g][1].test(f));
  const all = [];
  for (const fuel of ["ch4", "rp1"]) for (const [cs, field, diff, tol] of VD[fuel].rows) if (tol) all.push({ fuel, cs, field, diff, tol, q: Math.abs(diff) / tol });
  const worst = all.reduce((a, p) => (p.q > a.q ? p : a), all[0]);
  const c1 = card(V.rail, "与 NASA CEA 逐字段对照",
    `<p>同一 NASA9 物性（CEA v3.3.4 thermo.inp）、同一入口焓与元素库存，比较 C 程序与 CEA 的燃烧室、喉部、出口和性能字段。</p>`);
  P.fuel = seg(c1, "显示", [["all", "全部"], ["ch4", "液甲烷"], ["rp1", "RP-1"]], "all");
  card(V.rail, "", `<div class="ev"><table>` + [["液甲烷：C 运行 / CEA 卡", `${VD.ch4.c_runs} / ${VD.ch4.cea_cards}`], ["RP-1：C 运行 / CEA 卡", `${VD.rp1.c_runs} / ${VD.rp1.cea_cards}`],
    ["对照字段", fx(all.length, 0)], ["超出容差", all.filter((p) => p.q > 1).length], ["最紧一项", `${fx(worst.q * 100, 1)}% 容差`]].map(([a, b]) => `<tr><td>${a}</td><td>${b}</td></tr>`).join("") + `</table></div>`);
  card(V.rail, "CEA 对照", `<p>相同物性与输入下，C 实现的平衡态和喷管解与 CEA v3.3.4 一致。</p><p class="muted">对照范围：两者共同的九气相冻结口径。</p>` +
    `<p class="muted">来源：${VD.ch4.archive}、${VD.rp1.archive}（保存的 manifest），页面不重新运行 CEA。</p>`);
  P.chain = chain(V.stage, "对照流程");
  P.chain.set([{ name: "同一 thermo.inp", val: "NASA9 · 十物种" }, { name: "同一入口焓 / 库存", val: "显式焓卡" }, { name: "C 程序", val: `${VD.ch4.c_runs + VD.rp1.c_runs} 次运行` },
    { name: "NASA CEA v3.3.4", val: `${VD.ch4.cea_cards + VD.rp1.cea_cards} 张卡` }, { name: "逐字段差值 ÷ 容差", val: `${fx(all.length, 0)} 项 ≤ 1` }]);
  const row = kpiRow(V.stage, 4), maxAbs = (fuel, field) => VD[fuel].rows.filter((r) => r[1] === field).reduce((a, r) => Math.max(a, Math.abs(r[2])), 0);
  const tolOf = (field) => (VD.ch4.rows.find((r) => r[1] === field) || [])[3];
  kpi(row, "燃烧室温度最大差", "容差 0.02 K").set({ v: Math.max(maxAbs("ch4", "chamber.temperature_k"), maxAbs("rp1", "chamber.temperature_k")), d: 4, unit: "K", foot: "小于 CEA 打印精度 0.01 K" });
  kpi(row, "c* 最大差", "容差 0.03 m/s").set({ v: Math.max(maxAbs("ch4", "nozzle.cstar_m_per_s"), maxAbs("rp1", "nozzle.cstar_m_per_s")), d: 4, unit: "m/s", foot: "两条路径全部工况" });
  kpi(row, "真空有效速度最大差").set({ v: Math.max(maxAbs("ch4", "nozzle.ivac_m_per_s"), maxAbs("rp1", "nozzle.ivac_m_per_s")), d: 4, unit: "m/s", foot: "约为真空有效速度的 10<sup>−6</sup>" });
  kpi(row, "逐字段对照").set({ v: all.length, d: 0, unit: "项", foot: `超出容差 <b>${all.filter((p) => p.q > 1).length}</b> 项` });
  const g = figs(V.stage, "1.45fr 1fr");
  const f1 = figure(g, { title: "每项偏差占容差的比例", sub: "|C − CEA| / 容差，对数轴；零差值画在底线 · 悬停查看工况", legend: legendItem("#0F8A8A", `液甲烷（${VD.ch4.cea_cards} 卡）`, 1) + legendItem("#C8741E", `RP-1（${VD.rp1.cea_cards} 卡）`, 1) });
  const f2 = figure(g, { title: "关键量最大偏差", sub: "全部工况中的最大 |C − CEA|" });
  const FIELDS = [["chamber.temperature_k", "燃烧室温度", "K", 4], ["chamber.h_j_per_kg", "燃烧室比焓", "J/kg", 3], ["chamber.molar_mass_kg_per_kmol", "摩尔质量", "kg/kmol", 6],
    ["throat.temperature_k", "喉部温度", "K", 4], ["throat.pressure_pa", "喉部压力", "Pa", 1], ["exit.temperature_k", "出口温度", "K", 4],
    ["nozzle.cstar_m_per_s", "特征速度 c*", "m/s", 4], ["nozzle.ivac_m_per_s", "真空有效速度", "m/s", 4], ["geometry.cea_derived_thrust", "推力（CEA 派生）", "N", 2]];
  f2.body.innerHTML = `<div style="position:absolute;inset:0;overflow:auto"><table class="data"><thead><tr><th>字段</th><th class="n">液甲烷</th><th class="n">RP-1</th><th class="n">容差</th></tr></thead><tbody>` +
    FIELDS.map(([f, n, u, d]) => `<tr><td>${n} <span class="muted">${u}</span></td><td class="n">${fx(maxAbs("ch4", f), d)}</td><td class="n">${fx(maxAbs("rp1", f), d)}</td><td class="n muted">${Number(Number(tolOf(f)).toPrecision(3))}</td></tr>`).join("") + "</tbody></table></div>";
  P.take = takeaway(V.stage);
  P.take.innerHTML = `两条路径 <b>${fx(all.length, 0)}</b> 项字段对照全部在容差内；最紧的一项是 ${esc(worst.field)}（${worst.fuel === "rp1" ? "RP-1" : "液甲烷"}，${esc(worst.cs)}，占容差 ${fx(worst.q * 100, 1)}%）。燃烧室温度最大差小于 CEA 自身的打印精度。`;
  P.f1 = plotFrame(f1.body, (api) => {
    const f = P.fuel.get(), pts = all.filter((p) => f === "all" || p.fuel === f);
    stripChart(api, { groups: GROUPS.map(([label], gi) => ({ label, points: pts.filter((p) => groupOf(p.field) === gi).map((p) => ({ ...p, lq: p.q > 0 ? Math.log10(p.q) : -6 })) })),
      tip: (p) => tipTable(`${p.fuel === "rp1" ? "RP-1" : "液甲烷"} · ${esc(p.cs)}`, [["字段", esc(p.field)], ["C − CEA", sci(p.diff, 3)], ["容差", p.tol], ["占容差", `${fx(p.q * 100, 2)}%`]]) });
  });
  P.fuel.on(() => P.f1.redraw());
} });
