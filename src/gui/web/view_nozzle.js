"use strict";
/* Frozen nozzle at the shared chamber point: regime assessment, attached solve,
 * station profile and an area-ratio x ambient sweep. */
(() => {
  const AMB = [[0, "真空", "var(--accent)"], [5000, "5 kPa", "#8b5cf6"], [50000, "50 kPa", "var(--warn)"], [101325, "海平面", "var(--hot)"]];
  const ARS = logspace(1.5, 150, 40);
  let v, ctl = {}, k, banner, schemHost, isoChart, setIso, profChart, setProf, strip, point = null, sweep = null, sweepKey = "";
  const runPoint = RP.channel("nozzle", (env) => { point = env; paint(); });
  const runSweep = RP.channel("nozzle_sweep", (env) => { sweep = env.ok ? env.result : null; paintIso(); });
  const colorOf = (pa) => {
    const c = (AMB.find((a) => a[0] === pa) || [0, 0, "var(--ink-2)"])[2];
    return c.startsWith("var(") ? css(c.slice(4, -1)) : c;
  };
  const nameOf = (pa) => (AMB.find((a) => a[0] === pa) || [0, F.ambient(pa)])[1];

  function update() {
    const pas = AMB.map((a) => a[0]); if (!pas.includes(S.pa)) pas.push(S.pa);
    const sa = pointArgs({ at: S.at, ars: ARS, pas }), key = JSON.stringify(sa);
    if (key !== sweepKey) { sweepKey = key; runSweep(sa); }
    runPoint(pointArgs({ ar: S.ar, pa: S.pa, at: S.at }));
    Bus.emit("point");
  }
  function syncControls() {
    ctl.fuel.set(S.fuel); ctl.of.range(FUEL[S.fuel].of[0], FUEL[S.fuel].of[1]); ctl.of.set(S.p.of);
    ctl.ar.set(S.ar); ctl.amb.set(AMB.some((a) => a[0] === S.pa) ? S.pa : "x"); ctl.pa.set(S.pa / 1e3); ctl.at.set(S.at);
  }

  function paintIso() {
    if (!sweep) return;
    const series = [];
    sweep.pas.forEach((pa, j) => {
      const isp = sweep.isp[j], code = sweep.regime[j], c = colorOf(pa);
      const solid = isp.map((y, i) => (code[i] === 0 ? y : null));
      const dash = isp.map((y, i) => (code[i] !== 0 || (i + 1 < code.length && code[i + 1] !== 0) ? y : null));
      series.push({ name: `${nameOf(pa)} 附着解`, x: sweep.ars, y: solid, color: c, format: (y) => `${F.n(y, 1)} s`, rejected: "过膨胀" });
      if (dash.some(finite)) series.push({ name: `${nameOf(pa)} 理想参考`, x: sweep.ars, y: dash, color: c, dash: true, noTip: true });
    });
    const j = sweep.pas.indexOf(S.pa), matched = j >= 0 ? sweep.matched_ar[j] : null;
    const r = point && point.ok ? point.result : null;
    setIso({
      x: { label: "面积比 ε = Aₑ/Aₜ", log: true, domain: [ARS[0], ARS[ARS.length - 1]], tip: (x) => `ε = ${F.g(x, 3)}` },
      y: { label: "比冲 / s", pad: 0.04, domain: (() => { const all = sweep.isp.flat().filter(finite), hi = Math.max(...all); return [Math.max(Math.min(...all), hi * 0.62), hi * 1.02]; })() }, series,
      vlines: [finite(matched) && S.pa > 0 ? { x: matched, label: `匹配 ε ${F.n(matched, 2)}`, color: colorOf(S.pa) } : null,
               { x: S.ar, label: `当前 ε ${F.g(S.ar, 3)}`, color: css("--ink-2"), bottom: true }].filter(Boolean),
      markers: r ? [{ x: S.ar, y: r.attached.ok ? r.attached.isp : r.ideal.isp, color: colorOf(S.pa), r: 6 }] : [],
    });
    $("nz-legend").innerHTML = Chart.legend([...sweep.pas.map((pa) => ({ name: nameOf(pa), color: colorOf(pa) })), { name: "虚线：pₑ < pₐ 理想公式参考", color: css("--ink-3"), dash: true }]);
  }

  function paint() {
    if (!point.ok) {
      ["isp", "f", "mdot", "cf", "pe", "me"].forEach((id) => k.set(id, "—", "", "拒算", true));
      UI.banner(banner, "bad", "×", `<b>${STAGE_ZH[point.stage] || ""}拒算：${STATUS_ZH[point.status] || point.status}</b>`, `${point.status}: ${point.message}`);
      schemHost.innerHTML = errorCard(point); profChart.innerHTML = ""; strip.innerHTML = "";
      return;
    }
    const r = point.result, a = r.attached, id = r.ideal, rg = r.regime, ok = a.ok;
    const ref = ok ? a : { isp: id.isp, thrust: id.thrust, mdot: id.mdot };
    const note = ok ? undefined : "理想公式参考";
    k.set("isp", F.n(ref.isp, 2), "s", ok ? `真空 ${F.n(r.vacuum.isp, 2)} s` : note, !ok);
    k.set("f", F.n(ref.thrust / 1e3, 2), "kN", note, !ok);
    k.set("mdot", F.n(ref.mdot, 3), "kg/s", `c* ${F.n(id.cstar, 1)} m/s`);
    k.set("cf", ok ? F.n(a.cf, 4) : "—", "", ok ? `真空 ${F.n(r.vacuum.cf, 4)}` : "附着解拒算", !ok);
    k.set("pe", F.kpa(id.exit.gas.p), "kPa", r.pa > 0 ? `pₐ/pₑ = ${F.n(rg.pa_over_pe, 3)}` : "真空背压");
    k.set("me", F.n(id.exit.mach, 3), "", `Tₑ ${F.n(id.exit.gas.t, 0)} K · uₑ ${F.n(id.exit.u, 0)} m/s`);
    const mt = finite(rg.matched_ar) ? `匹配面积比 ε = ${F.n(rg.matched_ar, 2)}` : "";
    if (rg.name === "ideal_domain") {
      UI.banner(banner, "ok", "✓", r.pa === 0 ? `<b>真空附着膨胀：I<sub>sp</sub> ${F.n(a.isp, 2)} s，F ${F.n(a.thrust / 1e3, 1)} kN。</b> 出口 pₑ ${F.kpa(id.exit.gas.p)} kPa，Ma ${F.n(id.exit.mach, 2)}。`
        : `<b>pₑ ${F.kpa(id.exit.gas.p)} kPa ≥ pₐ ${F.kpa(r.pa)} kPa：附着膨胀，I<sub>sp</sub> ${F.n(a.isp, 2)} s。</b> ${mt}；比真空损失 ${F.n(r.vacuum.isp - a.isp, 2)} s。`);
    } else {
      const sep = rg.name === "separation_hint";
      UI.banner(banner, sep ? "bad" : "warn", "!", `<b>${sep ? "分离风险" : "过膨胀"}：pₐ/pₑ = ${F.n(rg.pa_over_pe, 2)}，附着解拒算。</b> ` +
        `${mt}（当前 ${F.g(r.ar, 3)}）。` + (sep ? `出口压力已低于 0.4·pₐ 经验参考，ε ${F.n(rg.separation_ar, 1)} 处达到。` : "") +
        ` 理想公式参考 I<sub>sp</sub> ${F.n(id.isp, 1)} s，仅作对照。`, `${a.status}: ${a.message}`);
    }
    const pr = r.profile;
    Schem.nozzle(schemHost, r, (i, ev) => showTip(tipTable(`ε = ${F.g(pr.ar[i], 3)}`, [["马赫数", F.n(pr.mach[i], 3)], ["压力", `${F.kpa(pr.p[i])} kPa`], ["温度", `${F.n(pr.t[i], 0)} K`], ["速度", `${F.n(pr.u[i], 0)} m/s`]]), ev.clientX, ev.clientY));
    const lp = pr.p.map((p) => Math.log10(p));
    setProf({
      x: { label: "面积比 ε", log: true, domain: [1, Math.max(r.ar, 1.5)], tip: (x) => `ε = ${F.g(x, 3)}` },
      y: { label: "压力 (对数)", integer: true, domain: [Math.min(...lp, r.pa > 0 ? Math.log10(r.pa) : Infinity) - 0.2, Math.max(...lp) + 0.1], format: (t) => (Math.abs(t - Math.round(t)) < 1e-6 ? ["1 Pa", "10 Pa", "100 Pa", "1 kPa", "10 kPa", "100 kPa", "1 MPa", "10 MPa", "100 MPa"][Math.round(t)] || "" : "") },
      y2: { label: "马赫数" },
      series: [{ name: "静压", x: pr.ar, y: lp, color: css("--accent"), format: (y) => `${F.kpa(10 ** y)} kPa` },
               { name: "马赫数", x: pr.ar, y: pr.mach, axis: 2, color: css("--hot"), format: (y) => F.n(y, 3) }],
      hlines: r.pa > 0 ? [{ y: Math.log10(r.pa), label: `环境 pₐ ${F.ambient(r.pa)}`, color: css("--bad") }] : [],
    });
    strip.innerHTML = UI.strip([
      ["特征速度 c*", `${F.n(id.cstar, 1)} m/s`], ["真空有效排速", `${F.n(id.c_vac, 1)} m/s`], ["真空比冲", `${F.n(r.vacuum.isp, 2)} s`],
      ["出口面积 Aₑ", `${F.g(r.vacuum.exit_area, 4)} m²`], ["匹配面积比", finite(rg.matched_ar) ? F.n(rg.matched_ar, 2) : "—"],
      ["连续性残差", F.sci(r.vacuum.continuity_residual, 1)]]);
  }

  App.register("nozzle", {
    mount() {
      v = UI.view("nozzle", "喷管 · 冻结流膨胀", "以燃烧室平衡成分冻结膨胀，固定喉部面积求流量、推力与比冲；按背压判别附着、过膨胀与分离风险", {
        input: ["燃烧室工作点（推进剂、O/F，与燃烧室页共用）", "面积比 ε = 出口面积/喉部面积", "环境压力 pₐ（真空、高空、海平面或自定义）与喉部面积 Aₜ"],
        output: ["比冲 I<sub>sp</sub>、推力 F、质量流量 ṁ、推力系数 C<sub>F</sub>", "出口压力 pₑ、出口马赫数；状态条判别附着 / 过膨胀 / 分离风险", "推力室温度示意、比冲–面积比曲线、沿程压力与马赫数"],
        steps: ["拖面积比滑块看比冲变化；切换背压看同一喷管在不同高度的表现", "pₑ &lt; pₐ 时附着解拒算，灰色数值为理想公式参考", "“海平面 ε40”预设直接演示过膨胀拒算"],
      }, () => point && { inputs: pointArgs({ ar: S.ar, pa: S.pa, at: S.at }), outputs: point });
      const body = el("div");
      body.appendChild(el("div", { class: "group-title" }, "燃烧室工作点（与燃烧室页共用）"));
      ctl.fuel = UI.seg([{ value: "ch4", label: "液甲烷 / 液氧", color: "var(--ch4)" }, { value: "rp1", label: "RP-1 / 液氧", color: "var(--rp1)" }], S.fuel, (f) => { S.fuel = f; syncControls(); update(); });
      ctl.of = UI.slider({ label: "混合比", sym: "O/F", min: 0.5, max: 4.5, value: S.p.of, step: 0.01, digits: 2, onChange: (x) => { S.p.of = x; update(); } });
      [ctl.fuel.node, ctl.of.node].forEach((n) => body.appendChild(n));
      ctl.of.node.style.marginTop = "12px";
      body.appendChild(el("div", { class: "group-title", style: "margin-top:14px" }, "喷管与环境"));
      ctl.ar = UI.slider({ label: "面积比", sym: "Aₑ/Aₜ", min: 1.5, max: 150, value: S.ar, log: true, digits: 2, scale: ["1.5", "15", "150"], onChange: (x) => { S.ar = x; update(); } });
      ctl.amb = UI.seg([...AMB.map((a) => ({ value: a[0], label: a[1] })), { value: "x", label: "自定义" }], S.pa, (p) => { if (p !== "x") { S.pa = p; ctl.pa.set(p / 1e3); update(); } }, true);
      ctl.pa = UI.slider({ label: "环境压力", sym: "pₐ", unit: "kPa", min: 0, max: 110, value: S.pa / 1e3, step: 0.1, digits: 1, onChange: (x) => { S.pa = Math.round(x * 1e3); ctl.amb.set(AMB.some((a) => a[0] === S.pa) ? S.pa : "x"); update(); } });
      ctl.at = UI.slider({ label: "喉部面积", sym: "Aₜ", unit: "m²", min: 0.001, max: 0.1, value: S.at, log: true, digits: 4, onChange: (x) => { S.at = x; update(); } });
      [ctl.ar.node, ctl.amb.node, ctl.pa.node, ctl.at.node].forEach((n) => body.appendChild(n));
      ctl.pa.node.style.marginTop = "12px";
      body.appendChild(UI.chips([
        { label: "真空 ε40", ar: 40, pa: 0 }, { label: "海平面 ε10", ar: 10, pa: 101325 },
        { label: "海平面 ε40", ar: 40, pa: 101325, danger: true, title: "过膨胀：演示附着解拒算与分离提示" }], (it) => { S.ar = it.ar; S.pa = it.pa; syncControls(); update(); }));
      const panel = el("div", { class: "panel" }); panel.appendChild(UI.card("输入", "", body));
      const res = el("div", { class: "results" });
      k = UI.kpis([{ id: "isp", label: "比冲", sym: "I<sub>sp</sub>", color: "var(--accent)", tip: "Isp = F/(ṁ·g₀)，单位秒" },
        { id: "f", label: "推力", sym: "F", color: "var(--hot)", tip: "F = ṁ·uₑ + (pₑ − pₐ)·Aₑ" },
        { id: "mdot", label: "质量流量", sym: "ṁ", color: "var(--ch4)", tip: "由喉部临界流量确定：ṁ = p꜀·Aₜ/c*" },
        { id: "cf", label: "推力系数", sym: "C<sub>F</sub>", color: "#8b5cf6", tip: "CF = F/(p꜀·Aₜ)，衡量喷管膨胀效果" },
        { id: "pe", label: "出口压力", sym: "pₑ", color: "var(--warn)", tip: "pₑ ≥ pₐ 为附着膨胀；pₑ < pₐ 为过膨胀" },
        { id: "me", label: "出口马赫数", sym: "Maₑ", color: "var(--ox)", tip: "出口截面气流马赫数" }]);
      banner = el("div", { class: "banner info" });
      schemHost = el("div", { class: "chart short nozzle-wrap" });
      isoChart = el("div", { class: "chart" }); setIso = Chart.mount(isoChart);
      profChart = el("div", { class: "chart" }); setProf = Chart.mount(profChart);
      const isoCard = UI.card("比冲 – 面积比", "四种背压", isoChart); isoCard.appendChild(el("div", { id: "nz-legend", style: "padding-bottom:10px" }));
      const grid = el("div", { class: "grid-2" }); grid.appendChild(isoCard); grid.appendChild(UI.card("沿程参数", "冻结等熵膨胀", profChart));
      strip = el("div");
      [k.node, banner, UI.card("推力室示意", "轮廓按 √ε 缩放，颜色为计算的沿程温度；悬停查看站点", schemHost), grid, strip].forEach((n) => res.appendChild(n));
      res.appendChild(el("p", { class: "note" }, "<b>适用域</b> 附着解只覆盖 pₑ ≥ pₐ（无激波模型）。过膨胀时程序拒算附着解，另给理想公式参考值和 0.4·pₐ 经验分离提示，不作分离预测。"));
      const work = el("div", { class: "work" }); work.appendChild(panel); work.appendChild(res); v.appendChild(work);
      Bus.on((w) => { if (w === "theme" && point) { paint(); paintIso(); } });
    },
    show() { syncControls(); update(); },
    cmd: () => (S.fuel === "ch4" ? cliPoint("regime", S.ar, S.pa, S.at) : cliPoint("frozen", S.ar, S.pa, S.at)),
  });
})();
