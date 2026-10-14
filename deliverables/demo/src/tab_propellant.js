/* Tab: liquid CH4 vs fixed RP-1 in the same thrust chamber (same Pc, At, area ratio, back pressure). */
TABS.push({ id: "propellant", title: "推进剂取舍", init() {
  const V = view("propellant"), P = {};
  const c1 = card(V.rail, "同一推力室，换推进剂", `<p>Pc = 10 MPa，A<sub>t</sub> = 0.01 m²，九气相 HP + 燃烧室冻结喷管；两种推进剂入口各自保留。</p>`);
  P.ch4 = slider(c1, { label: `<span class="dot" style="background:var(--ch4)"></span>甲烷 O/F`, values: AX.ch4_of, value: 2.6, fmt: ofKey, color: "var(--ch4)" });
  P.rp1 = slider(c1, { label: `<span class="dot" style="background:var(--rp1)"></span>RP-1 O/F`, values: AX.rp1_of, value: 2.6, fmt: ofKey, color: "var(--rp1)" });
  P.lock = checkbox(c1, "两者取相同 O/F", true);
  P.ar = slider(c1, { label: "喷管面积比 A<sub>e</sub>/A<sub>t</sub>", values: AX.area_ratios, value: 10, ticks: [2, 60] });
  P.env = seg(c1, "环境背压", ENV, 0);
  const peakIsp = (fuel, ofs) => peakOf(ofs.map((r) => [r, gridPt(fuel, r, P.ar.get(), P.env.get())]).filter(([, p]) => ok(p)).map(([r, p]) => [r, p.isp]));
  presets(c1, [["报告口径 2.6/2.6", () => { P.lock.checked = true; P.ar.set(10, true); P.env.set(0, true); P.ch4.set(2.6); }],
    ["各自比冲峰值", () => { P.lock.checked = false; P.ch4.set(peakIsp("ch4", AX.ch4_of)[0], true); P.rp1.set(peakIsp("rp1", AX.rp1_of)[0]); }],
    ["推力差变号 2.9", () => { P.lock.checked = true; P.ch4.set(2.9); }]]);
  card(V.rail, "", `<p><b>入口</b>：${DATA.provenance.inlets.ch4}；${DATA.provenance.inlets.rp1}。</p>` +
    `<p class="muted">甲烷 O/F 2.0–4.0；RP-1 O/F 2.2–4.0。方法成对比较。</p>`);
  P.ev1 = evidence(V.rail, "甲烷侧证据"); P.ev2 = evidence(V.rail, "RP-1 侧证据");
  P.chain = chain(V.stage, "C 调用链");
  const row = kpiRow(V.stage, 4);
  P.k = [kpi(row, "比冲 I<sub>sp</sub>", "甲烷 ｜ RP-1"), kpi(row, "推力 F", "甲烷 ｜ RP-1"), kpi(row, "质量流量 ṁ", "甲烷 ｜ RP-1"), kpi(row, "特征速度 c*", "甲烷 ｜ RP-1")];
  const g = figs(V.stage, "1.15fr 1fr");
  const f1 = figure(g, { title: "比冲随 O/F", sub: "当前面积比与背压 · ▼ 为各自峰值 · 点击或拖动选 O/F" });
  const f2 = figure(g, { title: "甲烷相对 RP-1：比冲涨在流量上，不在推力上", sub: "同 O/F 逐点 (CH₄ − RP-1)/RP-1 · 推力线即 C<sub>F</sub> 之差（Pc、At 相同）" });
  P.take = takeaway(V.stage);
  const env = () => [P.ar.get(), P.env.get()];
  const curve = (fuel, ofs) => ofs.map((r) => [r, gridPt(fuel, r, ...env())]).filter(([, p]) => ok(p)).map(([r, p]) => [r, p.isp]);
  P.f1 = plotFrame(f1.body, (api) => {
    const cC = curve("ch4", AX.ch4_of), cR = curve("rp1", AX.rp1_of), ys = [...cC, ...cR].map((p) => p[1]);
    if (!ys.length) { api.content.innerHTML = el("text", { x: api.w / 2, y: api.h / 2, "text-anchor": "middle", fill: "#B3261E" }, "该面积比在此背压下全部过膨胀，C 拒算"); api.state = null; return; }
    const a = gridPt("ch4", P.ch4.get(), ...env()), b = gridPt("rp1", P.rp1.get(), ...env()), pc = peakOf(cC), pr = cR.length ? peakOf(cR) : null;
    lineChart(api, { pick: (x) => { if (AX.ch4_of.includes(x)) P.ch4.set(x); },
      series: [{ pts: cR, color: "var(--rp1)", end: "RP-1", name: "RP-1", fmt: (v) => `${fx(v, 2)} s` }, { pts: cC, color: "var(--ch4)", end: "液甲烷", name: "液甲烷", fmt: (v) => `${fx(v, 2)} s` }],
      marks: [{ x: pc[0], y: pc[1], kind: "peak", color: "#0F8A8A", label: `${fx(pc[1], 1)} s @ ${ofKey(pc[0])}` },
        ...(pr ? [{ x: pr[0], y: pr[1], kind: "peak", color: "#C8741E", label: `${fx(pr[1], 1)} s @ ${ofKey(pr[0])}` }] : []),
        ...(ok(a) ? [{ x: P.ch4.get(), y: a.isp, color: "#0F8A8A" }] : []), ...(ok(b) ? [{ x: P.rp1.get(), y: b.isp, color: "#C8741E" }] : [])],
      x: { domain: [1.95, 4.05], ticks: [2, 2.4, 2.8, 3.2, 3.6, 4], title: "氧燃比 O/F（质量）", name: "O/F", fmtTip: ofKey },
      y: { domain: padDomain(Math.min(...ys), Math.max(...ys), 0.14), d: 0, title: "比冲 I<sub>sp</sub> / s" } });
  });
  P.f2 = plotFrame(f2.body, (api) => {
    const common = AX.ch4_of.filter((r) => AX.rp1_of.includes(r)).map((r) => [r, gridPt("ch4", r, ...env()), gridPt("rp1", r, ...env())]).filter(([, a, b]) => ok(a) && ok(b));
    if (!common.length) { api.content.innerHTML = el("text", { x: api.w / 2, y: api.h / 2, "text-anchor": "middle", fill: "#B3261E" }, "无共同可解点"); api.state = null; return; }
    const rel = (k) => common.map(([r, a, b]) => [r, pct(a[k], b[k])]), all = ["isp", "mdot", "f"].flatMap((k) => rel(k).map((p) => p[1]));
    lineChart(api, { pick: (x) => { P.lock.checked = true; P.ch4.set(x); },
      series: [{ pts: rel("isp"), color: "#1F5FBF", end: "比冲", name: "比冲", fmt: (v) => `${sgn(v, 2)}%` },
        { pts: rel("mdot"), color: "#2E9E6A", end: "流量", name: "质量流量", fmt: (v) => `${sgn(v, 2)}%` },
        { pts: rel("f"), color: "#1A2233", width: 3, end: "推力", name: "推力", fmt: (v) => `${sgn(v, 3)}%` }],
      hlines: [{ y: 0, color: "#9AA4B5" }], vlines: P.lock.checked ? [{ x: P.ch4.get(), color: "#7A8496", dash: "4 4" }] : [],
      x: { domain: [2.15, 4.05], ticks: [2.2, 2.6, 3, 3.4, 3.8], title: "共同 O/F", name: "O/F", fmtTip: ofKey },
      y: { domain: padDomain(Math.min(0, ...all), Math.max(0, ...all), 0.1), d: 0, fmt: (t) => `${t > 0 ? "+" : ""}${t}%`, title: "相对差 %" } });
  });
  const pairKpi = (k, field, d, unit, scale = 1, a, b) => {
    if (!ok(a) || !ok(b)) { k.set({ html: `<div class="pair"><div>${ok(a) ? `<div class="v" style="color:var(--ch4)">${fx(a[field] * scale, d)}</div>` : '<div class="refused">✕ 拒算</div>'}</div><div>${ok(b) ? `<div class="v" style="color:var(--rp1)">${fx(b[field] * scale, d)}</div>` : '<div class="refused">✕ 拒算</div>'}</div></div>`, foot: "至少一侧过膨胀被 C 拒算" }); return; }
    k.set({ pair: [{ v: a[field] * scale, d, unit, cls: "" }, { v: b[field] * scale, d, unit }],
      foot: `甲烷 − RP-1：<b>${sgn((a[field] - b[field]) * scale, d)} ${unit}</b>（${sgn(pct(a[field], b[field]), 2)}%）` });
    k.el.querySelectorAll(".v")[0].style.color = "var(--ch4)"; k.el.querySelectorAll(".v")[1].style.color = "var(--rp1)";
  };
  function render() {
    const [ar, pa] = env(), a = gridPt("ch4", P.ch4.get(), ar, pa), b = gridPt("rp1", P.rp1.get(), ar, pa);
    pairKpi(P.k[0], "isp", 2, "s", 1, a, b); pairKpi(P.k[1], "f", 2, "kN", 1e-3, a, b); pairKpi(P.k[2], "mdot", 2, "kg/s", 1, a, b); pairKpi(P.k[3], "cstar", 1, "m/s", 1, a, b);
    const st = (p) => (ok(p) ? "ok" : "bad");
    P.chain.set([{ name: "CH₄ 查表 + HP", val: ok(a) ? `${a.d[0]} 次 · ${fx(a.tc, 0)} K` : "", state: st(a) }, { name: "RP-1 指定焓 + HP", val: ok(b) ? `${b.d[0]} 次 · ${fx(b.tc, 0)} K` : "", state: st(b) },
      { name: `冻结喷管 ε${ar}`, val: `背压 ${kpa(pa)} kPa`, state: ok(a) && ok(b) ? "ok" : "bad" }, { name: "同几何成对相减", val: ok(a) && ok(b) ? `ΔIsp ${sgn(a.isp - b.isp, 2)} s` : "不可比", state: ok(a) && ok(b) ? "ok" : "skip" }]);
    const evRows = (p) => (ok(p) ? [["HP 外层 / Newton", `${p.d[0]} / ${p.d[1]}`], ["元素最大残差", sci(p.d[2])], ["焓残差", `${sci(p.d[3])} J/kg`], ["石墨活度", sci(p.ac, 2)]] : [["状态", p.status], ["原因", "背压高于理想出口压力"]]);
    P.ev1.set(evRows(a), command("ch4", { of: ofKey(P.ch4.get()), ar, pa })); P.ev2.set(evRows(b), command("rp1", { of: ofKey(P.rp1.get()), ar, pa }));
    if (ok(a) && ok(b)) {
      P.take.innerHTML = `同 P<sub>c</sub>、A<sub>t</sub> 时 <b>F = C<sub>F</sub>·P<sub>c</sub>·A<sub>t</sub></b>，c* 不进入推力：C<sub>F</sub> ${fx(a.cf, 4)} 对 ${fx(b.cf, 4)}，推力只差 <b>${sgn(pct(a.f, b.f), 2)}%</b>。` +
        `甲烷 c* 高 ${sgn(a.cstar - b.cstar, 1)} m/s，由 <b>ṁ = P<sub>c</sub>A<sub>t</sub>/c*</b> 少用 <b>${fx(Math.abs(pct(a.mdot, b.mdot)), 2)}%</b> 推进剂，这就是比冲 ${sgn(a.isp - b.isp, 2)} s 的来源。` +
        (P.ch4.get() !== P.rp1.get() ? “” : “ 推力差变号点 “ + fx(cross, 1) + “。”);
    } else P.take.innerHTML = “过膨胀超出模型域，程序拒算。降低面积比或切换到更低背压。”;
    P.f1.redraw(); P.f2.redraw();
  }
  P.ch4.on(() => { if (P.lock.checked) { if (AX.rp1_of.includes(P.ch4.get())) P.rp1.set(P.ch4.get(), true); else P.lock.checked = false; } render(); });
  P.rp1.on(() => { if (P.lock.checked) { if (AX.ch4_of.includes(P.rp1.get())) P.ch4.set(P.rp1.get(), true); else P.lock.checked = false; } render(); });
  P.lock.addEventListener("change", () => { if (P.lock.checked) P.rp1.set(P.ch4.get(), true); render(); });
  P.ar.on(render); P.env.on(render);
  render();
} });
