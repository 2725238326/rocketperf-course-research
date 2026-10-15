"use strict";
/* Tab: liquid CH4 vs fixed RP-1 in the same thrust chamber (same Pc, At, area ratio, back pressure).
 * One compare call returns the selected pair plus a same-O/F sweep over the RP-1 method domain. */
TABS.push({ id: "propellant", title: "推进剂取舍", init() {
  const V = view("propellant"), P = {};
  let env = null;
  const c1 = card(V.rail, "同一推力室，换推进剂", `<p>Pc = 10 MPa，A<sub>t</sub> = 0.01 m²，九气相 HP + 燃烧室冻结喷管；两种推进剂入口各自保留。</p>`);
  P.ch4 = slider(c1, { label: `<span class="dot" style="background:var(--ch4)"></span>甲烷 O/F`, name: "甲烷 O/F", min: 2.0, max: 4.0, step: 0.01, value: 2.6, ticks: [2, 4], color: "var(--ch4)" });
  P.rp1 = slider(c1, { label: `<span class="dot" style="background:var(--rp1)"></span>RP-1 O/F`, name: "RP-1 O/F", min: 2.2, max: 4.0, step: 0.01, value: 2.6, ticks: [2.2, 4], color: "var(--rp1)" });
  P.lock = checkbox(c1, "两者取相同 O/F", true);
  P.ar = slider(c1, { label: "喷管面积比 A<sub>e</sub>/A<sub>t</sub>", name: "面积比", min: 2, max: 60, step: 1, value: 10, digits: 0, ticks: [2, 60] });
  P.env = seg(c1, "环境背压", ENV, 0);
  presets(c1, [["报告口径 2.6/2.6", () => { P.lock.checked = true; P.ar.set(10, true); P.env.set(0, true); P.rp1.set(2.6, true); P.ch4.set(2.6); }],
    ["各自比冲峰值", () => { if (!env || !env.ok) return; P.lock.checked = false; P.ch4.set(peak("ch4_isp")[0], true); P.rp1.set(peak("rp1_isp")[0]); }],
    ["推力差变号 2.9", () => { P.lock.checked = true; P.rp1.set(2.9, true); P.ch4.set(2.9); }]]);
  card(V.rail, "", `<p><b>入口</b>：CoolProp 7.1.0 单相表 CH₄ 120 K / O₂ 100 K；CEA 指定 RP-1 298.15 K / O₂(L) 90.170 K。</p>` +
    `<p class="muted">RP-1 方法域 10 MPa、O/F 2.2–4.0。成对比较由 C 一次完成，任一侧越域整对拒算。</p>`);
  P.ev1 = evidence(V.rail, "甲烷侧证据"); P.ev2 = evidence(V.rail, "RP-1 侧证据");
  P.chain = chain(V.stage, "C 调用链");
  const row = kpiRow(V.stage, 4);
  P.k = [kpi(row, "比冲 I<sub>sp</sub>", "甲烷 ｜ RP-1"), kpi(row, "推力 F", "甲烷 ｜ RP-1"), kpi(row, "质量流量 ṁ", "甲烷 ｜ RP-1"), kpi(row, "特征速度 c*", "甲烷 ｜ RP-1")];
  const g = figs(V.stage, "1.15fr 1fr");
  const f1 = figure(g, { title: "比冲随 O/F", sub: "当前面积比与背压 · ▼ 为各自峰值 · 点击或拖动选 O/F" });
  const f2 = figure(g, { title: "甲烷相对 RP-1：比冲涨在流量上，不在推力上", sub: "同 O/F 逐点 (CH₄ − RP-1)/RP-1 · 推力线即 C<sub>F</sub> 之差（Pc、At 相同）" });
  P.take = takeaway(V.stage);
  const sw = () => env.result.sweep;
  const curve = (key) => sw().of.map((x, i) => [+x.toFixed(4), sw()[key][i]]).filter((p) => finite(p[1]));
  const peak = (key) => peakOf(curve(key));
  const pickBoth = (x) => { P.lock.checked = true; P.rp1.set(+x.toFixed(2), true); P.ch4.set(+x.toFixed(2)); };
  P.f1 = plotFrame(f1.body, (api) => {
    if (!env) return plotMessage(api, "C 计算中…");
    if (!env.ok) return plotMessage(api, "当前面积比在此背压下过膨胀，C 拒算", "#B3261E");
    const cC = curve("ch4_isp"), cR = curve("rp1_isp"), ys = [...cC, ...cR].map((p) => p[1]);
    if (!ys.length) return plotMessage(api, "扫描范围内无可解点", "#B3261E");
    const r = env.result, pc = peakOf(cC), pr = peakOf(cR);
    lineChart(api, { pick: pickBoth,
      series: [{ pts: cR, color: "var(--rp1)", end: "RP-1", name: "RP-1", fmt: (v) => `${fx(v, 2)} s` }, { pts: cC, color: "var(--ch4)", end: "液甲烷", name: "液甲烷", fmt: (v) => `${fx(v, 2)} s` }],
      marks: [{ x: pc[0], y: pc[1], kind: "peak", color: "#0F8A8A", label: `${fx(pc[1], 1)} s @ ${fx(pc[0], 1)}` },
        { x: pr[0], y: pr[1], kind: "peak", color: "#C8741E", label: `${fx(pr[1], 1)} s @ ${fx(pr[0], 1)}` },
        { x: r.ch4_of, y: r.ch4.isp, color: "#0F8A8A" }, { x: r.rp1_of, y: r.rp1.isp, color: "#C8741E" }],
      x: { domain: [2.15, 4.05], ticks: [2.2, 2.6, 3, 3.4, 3.8], title: "氧燃比 O/F（质量）", name: "O/F", fmtTip: (x) => fx(x, 1) },
      y: { domain: padDomain(Math.min(...ys), Math.max(...ys), 0.14), d: 0, title: "比冲 I<sub>sp</sub> / s" } });
  });
  P.f2 = plotFrame(f2.body, (api) => {
    if (!env) return plotMessage(api, "C 计算中…");
    if (!env.ok) return plotMessage(api, "无共同可解点", "#B3261E");
    const s = sw(), idx = s.of.map((_, i) => i).filter((i) => finite(s.ch4_isp[i]) && finite(s.rp1_isp[i]));
    const rel = (a, b) => idx.map((i) => [+s.of[i].toFixed(4), pct(s[a][i], s[b][i])]);
    const series = [{ pts: rel("ch4_isp", "rp1_isp"), color: "#1F5FBF", end: "比冲", name: "比冲", fmt: (v) => `${sgn(v, 2)}%` },
      { pts: rel("ch4_mdot", "rp1_mdot"), color: "#2E9E6A", end: "流量", name: "质量流量", fmt: (v) => `${sgn(v, 2)}%` },
      { pts: rel("ch4_thrust", "rp1_thrust"), color: "#1A2233", width: 3, end: "推力", name: "推力", fmt: (v) => `${sgn(v, 3)}%` }];
    const all = series.flatMap((x) => x.pts.map((p) => p[1]));
    lineChart(api, { pick: pickBoth, series, hlines: [{ y: 0, color: "#9AA4B5" }],
      vlines: P.lock.checked ? [{ x: P.ch4.get(), color: "#7A8496", dash: "4 4" }] : [],
      x: { domain: [2.15, 4.05], ticks: [2.2, 2.6, 3, 3.4, 3.8], title: "共同 O/F", name: "O/F", fmtTip: (x) => fx(x, 1) },
      y: { domain: padDomain(Math.min(0, ...all), Math.max(0, ...all), 0.1), d: 0, fmt: (t) => `${t > 0 ? "+" : ""}${t}%`, title: "相对差 %" } });
  });
  const pairKpi = (k, field, d, unit, scale, a, b) => {
    k.set({ pair: [{ v: a[field] * scale, d, unit }, { v: b[field] * scale, d, unit }],
      foot: `甲烷 − RP-1：<b>${sgn((a[field] - b[field]) * scale, d)} ${unit}</b>（${sgn(pct(a[field], b[field]), 2)}%）` });
    const vs = k.el.querySelectorAll(".v"); vs[0].style.color = "var(--ch4)"; vs[1].style.color = "var(--rp1)";
  };
  const run = RP.channel("compare", (e) => { env = e; render(); });
  const solve = () => run({ ch4_of: P.ch4.get(), rp1_of: P.rp1.get(), ar: P.ar.get(), pa: P.env.get(), at: AT, of_min: 2.2, of_max: 4.0, n: 19 });
  function render() {
    const ar = P.ar.get(), pa = P.env.get();
    if (env.ok) {
      const r = env.result, a = r.ch4, b = r.rp1;
      pairKpi(P.k[0], "isp", 2, "s", 1, a, b); pairKpi(P.k[1], "thrust", 2, "kN", 1e-3, a, b); pairKpi(P.k[2], "mdot", 2, "kg/s", 1, a, b); pairKpi(P.k[3], "cstar", 1, "m/s", 1, a, b);
      P.chain.set([{ name: "CH₄ 查表 + HP", val: `${fx(a.tc, 0)} K` }, { name: "RP-1 指定焓 + HP", val: `${fx(b.tc, 0)} K` },
        { name: `冻结喷管 ε${ar}`, val: `背压 ${kpa(pa)} kPa` }, { name: "同几何成对相减", val: `ΔIsp ${sgn(r.delta.isp, 2)} s` }]);
      const rows = (s) => [["燃烧室温度", `${fx(s.tc, 1)} K`], ["推力系数 C<sub>F</sub>", fx(s.cf, 4)], ["出口压力", `${kpa(s.pe)} kPa`], ["石墨活度", sci(s.graphite_activity, 2)]];
      P.ev1.set(rows(a), CMD.ch4(r.ch4_of, ar, pa)); P.ev2.set(rows(b), CMD.rp1(r.rp1_of, ar, pa));
      P.take.innerHTML = `同 P<sub>c</sub>、A<sub>t</sub> 时 <b>F = C<sub>F</sub>·P<sub>c</sub>·A<sub>t</sub></b>，c* 不进入推力：C<sub>F</sub> ${fx(a.cf, 4)} 对 ${fx(b.cf, 4)}，推力只差 <b>${sgn(pct(a.thrust, b.thrust), 2)}%</b>。` +
        `甲烷 c* 高 ${sgn(r.delta.cstar, 1)} m/s，由 <b>ṁ = P<sub>c</sub>A<sub>t</sub>/c*</b> 少用 <b>${fx(Math.abs(pct(a.mdot, b.mdot)), 2)}%</b> 推进剂，这就是比冲 ${sgn(r.delta.isp, 2)} s 的来源。` +
        (r.ch4_of === r.rp1_of ? " 同 O/F 下推力差随 O/F 变号。" : "");
    } else {
      P.k.forEach((k) => k.set({ refused: "C 拒算", foot: "成对比较整对拒绝" }));
      P.chain.set([{ name: "CH₄ / RP-1 HP", val: "" }, { name: `冻结喷管 ε${ar}`, val: `背压 ${kpa(pa)} kPa`, state: "bad" }, { name: "同几何成对相减", val: "不可比", state: "skip" }]);
      const rows = [["状态", env.status], ["C 消息", `<span style="font-family:var(--ff);white-space:normal">${esc(env.message)}</span>`]];
      P.ev1.set(rows, CMD.ch4(P.ch4.get(), ar, pa)); P.ev2.set(rows, CMD.rp1(P.rp1.get(), ar, pa));
      P.take.innerHTML = `背压 ${envName(pa)} 高于 ε${ar} 的理想出口压力，附着喷管超出模型域，C 拒算。降低面积比或切换到更低背压。`;
    }
    P.f1.redraw(); P.f2.redraw();
  }
  P.ch4.on(() => { if (P.lock.checked) { if (P.ch4.get() >= 2.2) P.rp1.set(P.ch4.get(), true); else P.lock.checked = false; } solve(); });
  P.rp1.on(() => { if (P.lock.checked) P.ch4.set(P.rp1.get(), true); solve(); });
  P.lock.addEventListener("change", () => { if (P.lock.checked) { P.rp1.set(clamp(P.ch4.get(), 2.2, 4), true); P.ch4.set(P.rp1.get(), true); } solve(); });
  P.ar.on(solve); P.env.on(solve);
  solve();
} });
