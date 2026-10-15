"use strict";
/* Combustion chamber: HP equilibrium at the operating point plus an O/F sweep. */
(() => {
  const SPECIES_COLOR = ["#60a5fa", "#2f7de1", "#0ea5e9", "#f59e0b", "#a16207", "#0d9488", "#93c5fd", "#ef4444", "#8b5cf6"];
  let v, ctl = {}, k, chart, setChart, bars, banner, strip, sweep = null, point = null, tab = "tc", sweepKey = "";
  const runPoint = RP.channel("chamber", (env) => { point = env; paintPoint(); paintChart(); });
  const runSweep = RP.channel("chamber_sweep", (env) => { sweep = env.ok ? env.result : null; paintChart(); });

  function sweepArgs() {
    const a = pointArgs(); delete a.of;
    const r = FUEL[S.fuel].of;
    return Object.assign(a, { of_min: r[0], of_max: r[1], n: S.fuel === "ch4" ? 41 : 19 });
  }
  function update() {
    const key = JSON.stringify(sweepArgs());
    if (key !== sweepKey) { sweepKey = key; runSweep(sweepArgs()); }
    runPoint(pointArgs());
    Bus.emit("point");
  }
  function applyFuel() {
    const f = FUEL[S.fuel], p = S.p;
    ctl.of.range(f.of[0], f.of[1]);
    ctl.pc.set(p.pc); ctl.of.set(p.of);
    ctl.pc.lock(S.fuel === "rp1" ? "RP-1 方法域固定 10 MPa" : "");
    ["tf", "to", "pf", "po"].forEach((id) => { if (p[id] !== undefined) ctl[id].set(p[id]); ctl[id].lock(S.fuel === "rp1" ? "指定反应物" : ""); });
    ctl.ofScale.innerHTML = `<span>${f.of[0]}</span><span>${((f.of[0] + f.of[1]) / 2).toFixed(1)}</span><span>${f.of[1]}</span>`;
    v.querySelectorAll(".ch4-only").forEach((n) => { n.hidden = S.fuel !== "ch4"; });
  }

  function bands() {
    if (!sweep) return [];
    const out = [], xs = sweep.of, step = xs[1] - xs[0];
    let start = null;
    xs.forEach((x, i) => {
      const bad = sweep.status[i] !== "ok";
      if (bad && start === null) start = i;
      if ((!bad || i === xs.length - 1) && start !== null) {
        const end = bad ? i : i - 1, carbon = /graphite/.test(sweep.message[start]);
        out.push({ from: xs[start] - step / 2, to: xs[end] + step / 2, label: carbon ? "凝聚碳 a꜀>1 · 拒算" : "超出适用域 · 拒算" });
        start = null;
      }
    });
    return out;
  }
  function paintChart() {
    if (!sweep) return;
    const of = S.p.of, ok = point && point.ok, r = ok ? point.result : null;
    const xs = sweep.of, base = { x: { label: "O/F 混合比", domain: [xs[0], xs[xs.length - 1]], tip: (x) => `O/F = ${F.n(x, 2)}` }, bands: bands(),
      vlines: [{ x: of, label: `当前 ${F.n(of, 2)}`, color: css("--accent"), bottom: true }] };
    const peakC = argmax(xs, sweep.cstar), peakT = argmax(xs, sweep.t);
    if (tab === "tc") {
      setChart(Object.assign(base, {
        y: { label: "T꜀ / K" }, y2: { label: "c* / (m/s)" },
        series: [{ name: "燃烧室温度 T꜀", x: xs, y: sweep.t, color: css("--hot"), format: (y) => `${F.n(y, 0)} K` },
                 { name: "特征速度 c*", x: xs, y: sweep.cstar, color: css("--accent"), axis: 2, format: (y) => `${F.n(y, 1)} m/s` }],
        markers: [peakT && { x: peakT.x, y: peakT.y, color: css("--hot"), label: `T꜀ 峰 O/F ${F.n(peakT.x, 2)}`, r: 4 },
                  peakC && { x: peakC.x, y: peakC.y, axis: 2, color: css("--accent"), label: `c* 峰 O/F ${F.n(peakC.x, 2)}`, r: 4, dy: 16 },
                  ok && { x: of, y: r.chamber.gas.t, color: css("--hot"), r: 6 },
                  ok && { x: of, y: r.cstar, axis: 2, color: css("--accent"), r: 6 }].filter(Boolean),
      }));
    } else if (tab === "ac") {
      const lg = sweep.graphite_activity.map((a) => (finite(a) && a > 0 ? Math.log10(a) : null));
      setChart(Object.assign(base, {
        y: { label: "lg a꜀", integer: true, format: (t) => `10^${t}` },
        series: [{ name: "石墨活度 a꜀", x: xs, y: lg, color: css("--warn"), area: true, format: (y) => F.sciText(10 ** y, 2) }],
        hlines: [{ y: 0, label: "a꜀ = 1 凝聚碳边界", color: css("--bad") }],
        markers: ok ? [{ x: of, y: Math.log10(r.chamber.graphite_activity), color: css("--warn"), r: 6 }] : [],
      }));
    } else {
      setChart(Object.assign(base, {
        y: { label: "M̄ / (kg/kmol)" }, y2: { label: "γ 冻结" },
        series: [{ name: "平均摩尔质量 M̄", x: xs, y: sweep.mw, color: css("--ch4"), format: (y) => F.n(y, 2) },
                 { name: "比热比 γ", x: xs, y: sweep.gamma, color: "#8b5cf6", axis: 2, format: (y) => F.n(y, 4) }],
        markers: ok ? [{ x: of, y: r.chamber.gas.mw, color: css("--ch4"), r: 6 }, { x: of, y: r.chamber.gas.gamma, axis: 2, color: "#8b5cf6", r: 6 }] : [],
      }));
    }
  }

  function paintPoint() {
    const of = S.p.of;
    if (!point.ok) {
      ["tc", "cstar", "mw", "gamma", "ac"].forEach((id) => k.set(id, "—", "", "拒算", true));
      const m = CARBON_RE.exec(point.message || "");
      UI.banner(banner, "bad", "×", m
        ? `<b>拒算：O/F ${F.n(of, 2)} 时石墨活度 a꜀ = ${m[1]} &gt; 1。</b> 凝聚碳在热力学上稳定，九组分气相模型不含 C(gr)，程序不外推。`
        : `<b>拒算：${STATUS_ZH[point.status] || point.status}</b>`, `${point.status}: ${point.message}`);
      bars.innerHTML = errorCard(point);
      strip.innerHTML = "";
      return;
    }
    const r = point.result, c = r.chamber, g = c.gas;
    k.set("tc", F.n(g.t, 1), "K");
    k.set("cstar", F.n(r.cstar, 1), "m/s");
    k.set("mw", F.n(g.mw, 3), "kg/kmol");
    k.set("gamma", F.n(g.gamma, 4), "", `c<sub>p</sub> ${F.n(g.cp, 0)} J/(kg·K)`);
    const ac = c.graphite_activity, pos = (Math.log10(Math.max(ac, 1e-7)) + 7) / 9;
    k.set("ac", F.sci(ac, 2), "", ac > 0.1 ? `距凝聚碳边界 ${F.n((1 - ac) * 100, 1)}%` : "远离凝聚碳边界");
    k.gauge("ac", pos, 7 / 9, ac > 0.5 ? css("--warn") : css("--ok"));
    const peakC = sweep && argmax(sweep.of, sweep.cstar), peakT = sweep && argmax(sweep.of, sweep.t);
    let text = `<b>O/F ${F.n(of, 2)}：T꜀ ${F.n(g.t, 0)} K，c* ${F.n(r.cstar, 1)} m/s。</b>`;
    if (peakC && peakT) text += ` 本扫描 c* 峰在 O/F ${F.n(peakC.x, 2)}，温度峰在 ${F.n(peakT.x, 2)}；c* 峰更偏富燃，因为富燃产物摩尔质量更小。`;
    UI.banner(banner, ac > 0.5 ? "warn" : "ok", ac > 0.5 ? "!" : "✓", text);
    const ids = App.info ? App.info.species : [];
    const order = g.x.map((x, i) => [x, i]).sort((a, b) => b[0] - a[0]), top = order[0][0];
    bars.innerHTML = `<div class="bars">${order.map(([x, i]) =>
      `<div class="bar"><span class="n">${SPECIES_HTML(ids[i] || "?")}</span><span class="tr"><b style="width:${(x / top) * 100}%;background:${SPECIES_COLOR[i]}"></b></span>` +
      `<span class="x">${x >= 1e-3 ? F.n(x * 100, 2) + "%" : F.sci(x, 2)}</span></div>`).join("")}</div>`;
    strip.innerHTML = UI.strip([
      ["HP 外层迭代", `${c.hp_iterations} 次`], ["平衡迭代", `${c.eq_iterations} 次`],
      ["元素守恒残差", F.sci(c.element_residual, 1)], ["焓残差", `${F.g(c.enthalpy_residual, 2)} J/kg`],
      ["入口混合焓", `${F.n(c.mixture_h / 1e3, 1)} kJ/kg`],
      ...(finite(c.fuel_density) ? [["燃料/氧密度", `${F.n(c.fuel_density, 1)} / ${F.n(c.oxidizer_density, 1)} kg/m³`]] : []),
    ]);
  }

  App.register("chamber", {
    mount() {
      v = UI.view("chamber", "燃烧室 · 化学平衡", "给定入口状态与室压，求九组分 CHO 理想气体的绝热等压平衡（HP），并检查凝聚碳稳定性", {
        input: ["推进剂：液甲烷/液氧 或 RP-1/液氧", "室压 p<sub>c</sub>（MPa）与混合比 O/F（氧/燃料质量比）", "入口温度、压力（折叠在“入口状态”内，一般不用改）"],
        output: ["燃烧室温度 T꜀、特征速度 c*、平均摩尔质量 M̄、比热比 γ", "石墨活度 a꜀：&gt;1 表示会析出固体碳，程序拒算", "产物组成（摩尔分数）与 O/F 扫描曲线"],
        steps: ["拖动滑块或在数字框输入后回车，结果即时更新", "点预设按钮快速切到典型工况；“凝聚碳区”演示拒算", "曲线可悬停读数；红色区域为 C 核心拒算的 O/F 范围"],
      }, () => point && { inputs: pointArgs(), outputs: point });
      const panel = el("div", { class: "panel" }), body = el("div");
      body.appendChild(el("div", { class: "group-title" }, "推进剂"));
      ctl.fuel = UI.seg([{ value: "ch4", label: "液甲烷 / 液氧", color: "var(--ch4)" }, { value: "rp1", label: "RP-1 / 液氧", color: "var(--rp1)" }],
        S.fuel, (f) => { S.fuel = f; applyFuel(); update(); });
      body.appendChild(ctl.fuel.node);
      body.appendChild(el("div", { class: "group-title", style: "margin-top:14px" }, "工作点"));
      ctl.pc = UI.slider({ label: "室压", sym: "p<sub>c</sub>", unit: "MPa", min: 1, max: 20, value: S.p.pc, step: 0.1, digits: 1, scale: ["1", "10", "20"], onChange: (x) => { S.p.pc = x; update(); } });
      ctl.of = UI.slider({ label: "混合比", sym: "O/F", unit: "", min: 0.5, max: 4.5, value: S.p.of, step: 0.01, digits: 2, scale: ["0.5", "2.5", "4.5"], onChange: (x) => { S.p.of = x; update(); } });
      ctl.ofScale = ctl.of.node.querySelector(".range-scale");
      body.appendChild(ctl.pc.node); body.appendChild(ctl.of.node);
      body.appendChild(UI.chips([
        { label: "主室 2.6", of: 2.6 }, { label: "c* 峰", peak: true }, { label: "发生器 1.0", of: 1.0, ch4: true },
        { label: "凝聚碳区 0.8", of: 0.8, ch4: true, danger: true, title: "演示 C 核心的显式拒算" }], (it) => {
        if (it.ch4 && S.fuel !== "ch4") { toast("该预设属于液甲烷工况"); return; }
        let of = it.of;
        if (it.peak) { const p = sweep && argmax(sweep.of, sweep.cstar); if (!p) return; of = +p.x.toFixed(2); }
        S.p.of = of; ctl.of.set(of); update();
      }));
      const more = el("details", { class: "more" }, "<summary>入口状态（液体物性查表）</summary>");
      const md = el("div");
      ctl.tf = UI.slider({ label: "燃料温度", sym: "T<sub>f</sub>", unit: "K", min: 100, max: 140, value: 120, step: 0.5, digits: 1, onChange: (x) => { S.p.tf = x; update(); } });
      ctl.pf = UI.slider({ label: "燃料压力", sym: "p<sub>f</sub>", unit: "MPa", min: 1, max: 20, value: 10, step: 0.1, digits: 1, onChange: (x) => { S.p.pf = x; update(); } });
      ctl.to = UI.slider({ label: "氧温度", sym: "T<sub>o</sub>", unit: "K", min: 80, max: 110, value: 100, step: 0.5, digits: 1, onChange: (x) => { S.p.to = x; update(); } });
      ctl.po = UI.slider({ label: "氧压力", sym: "p<sub>o</sub>", unit: "MPa", min: 1, max: 20, value: 10, step: 0.1, digits: 1, onChange: (x) => { S.p.po = x; update(); } });
      [ctl.tf, ctl.pf, ctl.to, ctl.po].forEach((c) => md.appendChild(c.node));
      md.appendChild(el("p", { class: "note" }, "甲烷 100–140 K、氧 80–110 K、1–20 MPa 单相液体查表；RP-1 使用 298.15 K / 90.170 K 指定反应物。"));
      more.appendChild(md); body.appendChild(more);
      panel.appendChild(UI.card("输入", "", body));
      const res = el("div", { class: "results" });
      k = UI.kpis([{ id: "tc", label: "燃烧室温度", sym: "T꜀", color: "var(--hot)", tip: "绝热等压平衡温度：入口总焓 = 产物焓" },
        { id: "cstar", label: "特征速度", sym: "c*", color: "var(--accent)", tip: "c* = p꜀·Aₜ/ṁ，只取决于燃烧室状态，衡量燃烧效能" },
        { id: "mw", label: "平均摩尔质量", sym: "M̄", color: "var(--ch4)", tip: "产物平均分子量；越小同温度下排速越高" },
        { id: "gamma", label: "冻结比热比", sym: "γ", color: "#8b5cf6", tip: "γ = c<sub>p</sub>/(c<sub>p</sub>−R)，成分冻结时的比热比".replace(/<\/?sub>/g, "") },
        { id: "ac", label: "石墨活度", sym: "a꜀", color: "var(--warn)", gauge: true, tip: "a꜀ > 1 时固体碳热力学稳定，九组分气相模型拒算；色条红线为 a꜀ = 1" }]);
      banner = el("div", { class: "banner info" });
      chart = el("div", { class: "chart tall" }); setChart = Chart.mount(chart);
      const tabs = UI.seg([{ value: "tc", label: "T꜀ 与 c*" }, { value: "ac", label: "石墨活度" }, { value: "mw", label: "M̄ 与 γ" }], tab, (t) => { tab = t; paintChart(); }, true);
      const cc = UI.card("O/F 扫描", "红色区域为 C 核心拒算", chart); cc.querySelector(".card-h").appendChild(tabs.node);
      bars = el("div"); strip = el("div");
      const grid = el("div", { class: "grid-3" }); grid.appendChild(cc); grid.appendChild(UI.card("燃烧产物组成", "摩尔分数", bars));
      [k.node, banner, grid, strip].forEach((n) => res.appendChild(n));
      res.appendChild(el("p", { class: "note" }, "<b>模型</b> 九组分 CHO 理想气体 HP 平衡（NASA9 / CEA v3.3.4 数据）。石墨活度 a꜀ &gt; 1 时凝聚碳热力学稳定，该状态超出气相模型，程序拒算并保留原因。"));
      const work = el("div", { class: "work" }); work.appendChild(panel); work.appendChild(res); v.appendChild(work);
      applyFuel();
      Bus.on((w) => { if (w === "theme") { paintChart(); if (point) paintPoint(); } if (w === "fuel-external") { ctl.fuel.set(S.fuel); applyFuel(); update(); } });
      update();
    },
    show() { ctl.fuel.set(S.fuel); applyFuel(); update(); },
    cmd: () => cliPoint("hp"),
  });
})();
