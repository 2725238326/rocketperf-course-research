"use strict";
/* Methane vs RP-1 at the same Pc, throat, area ratio and ambient (paired C solve). */
(() => {
  let v, ctl = {}, vs, banner, isp, setIsp, rel, setRel, env = null, linked = true;
  const C = { ch4_of: 2.6, rp1_of: 2.6, ar: 10, pa: 0, at: 0.01 };
  const run = RP.channel("compare", (e) => { env = e; paint(); });
  const update = () => { run({ ...C, of_min: 2.2, of_max: 4.0, n: 19 }); Bus.emit("cmd"); };
  const pct = (a, b) => (finite(a) && finite(b) ? (a / b - 1) * 100 : null);

  function row(label, a, b, fmt, unit, big) {
    const d = pct(a, b);
    return [`<div class="row${big ? " big" : ""}"><span>${label}</span><span>${fmt(a)} ${unit}</span></div>`,
            `<div class="row${big ? " big" : ""}"><span class="delta ${d > 0 ? "up" : "down"}">${F.pct(d, 2)}</span></div>`,
            `<div class="row${big ? " big" : ""}"><span>${label}</span><span>${fmt(b)} ${unit}</span></div>`];
  }
  function paint() {
    if (!env.ok) {
      vs.innerHTML = errorCard(env, "成对求解按同一契约失败：任一推进剂超域时整对结果不输出。");
      UI.banner(banner, "bad", "×", `<b>成对对比拒算：${STATUS_ZH[env.status] || env.status}</b>`, `${env.status}: ${env.message}`);
      return;
    }
    const r = env.result, a = r.ch4, b = r.rp1;
    const rows = [row("燃烧室温度 T꜀", a.tc, b.tc, (x) => F.n(x, 0), "K"), row("平均摩尔质量 M̄", a.mw, b.mw, (x) => F.n(x, 2), ""),
      row("特征速度 c*", a.cstar, b.cstar, (x) => F.n(x, 1), "m/s"), row("推力系数 C<sub>F</sub>", a.cf, b.cf, (x) => F.n(x, 4), ""),
      row("比冲 I<sub>sp</sub>", a.isp, b.isp, (x) => F.n(x, 2), "s", true), row("推力 F", a.thrust, b.thrust, (x) => F.n(x / 1e3, 2), "kN", true),
      row("质量流量 ṁ", a.mdot, b.mdot, (x) => F.n(x, 3), "kg/s", true), row("出口压力 pₑ", a.pe, b.pe, (x) => F.kpa(x), "kPa")];
    vs.innerHTML = `<div class="vs"><div class="col ch4"><h3><i class="sw"></i>液甲烷 / 液氧 · O/F ${F.n(r.ch4_of, 2)}</h3>${rows.map((x) => x[0]).join("")}</div>` +
      `<div class="mid"><h3>甲烷相对 RP-1</h3>${rows.map((x) => x[1]).join("")}</div>` +
      `<div class="col rp1"><h3>RP-1 / 液氧 · O/F ${F.n(r.rp1_of, 2)}</h3>${rows.map((x) => x[2]).join("")}</div></div>`;
    const dF = pct(a.thrust, b.thrust), dm = pct(a.mdot, b.mdot);
    UI.banner(banner, "info", "i", `<b>同 p<sub>c</sub> 10 MPa、A<sub>t</sub>、ε ${F.g(r.ar, 3)}、${F.ambient(r.pa)}：甲烷比冲 ${F.sign(r.delta.isp, 2)} s，推力 ${F.pct(dF, 2)}，流量 ${F.pct(dm, 2)}。</b> ` +
      `解读：喉部面积与室压固定时 ṁ = p<sub>c</sub>A<sub>t</sub>/c*，c* 高则流量少；推力由 C<sub>F</sub>·p<sub>c</sub>·A<sub>t</sub> 决定，比冲收益主要来自省下的流量。`);
    const sw = r.sweep, cross = zeroCrossing(sw.of, sw.of.map((_, i) => pct(sw.ch4_thrust[i], sw.rp1_thrust[i])));
    setIsp({
      x: { label: "O/F（两种推进剂取同值）", domain: [2.2, 4.0], tip: (x) => `O/F = ${F.n(x, 2)}` }, y: { label: "比冲 / s" },
      series: [{ name: "液甲烷 I<sub>sp</sub>", x: sw.of, y: sw.ch4_isp, color: css("--ch4"), format: (y) => `${F.n(y, 2)} s` },
               { name: "RP-1 I<sub>sp</sub>", x: sw.of, y: sw.rp1_isp, color: css("--rp1"), format: (y) => `${F.n(y, 2)} s` }],
      markers: [{ x: r.ch4_of, y: a.isp, color: css("--ch4"), r: 6 }, { x: r.rp1_of, y: b.isp, color: css("--rp1"), r: 6 }],
    });
    setRel({
      x: { label: "共同 O/F", domain: [2.2, 4.0], tip: (x) => `O/F = ${F.n(x, 2)}` }, y: { label: "甲烷相对 RP-1 / %", zero: true }, zero: true,
      series: [{ name: "比冲差", x: sw.of, y: sw.of.map((_, i) => pct(sw.ch4_isp[i], sw.rp1_isp[i])), color: css("--accent"), format: (y) => F.pct(y, 2) },
               { name: "流量差", x: sw.of, y: sw.of.map((_, i) => pct(sw.ch4_mdot[i], sw.rp1_mdot[i])), color: css("--warn"), format: (y) => F.pct(y, 2) },
               { name: "推力差", x: sw.of, y: sw.of.map((_, i) => pct(sw.ch4_thrust[i], sw.rp1_thrust[i])), color: css("--ink"), width: 2.8, format: (y) => F.pct(y, 2) }],
      vlines: cross ? [{ x: cross, label: `推力差变号 O/F ≈ ${F.n(cross, 2)}`, color: css("--ink") }] : [],
    });
  }

  App.register("compare", {
    mount() {
      v = UI.view("compare", "推进剂对比 · 液甲烷与 RP-1", "同一室压、喉部面积、面积比与背压下成对求解，比较 c*、流量、推力与比冲", {
        input: ["两种推进剂的 O/F（可锁定为相同值）", "共同面积比 ε 与环境压力；室压固定 10 MPa、喉部 0.01 m²"],
        output: ["左右两列为甲烷、RP-1 的 T꜀、c*、C<sub>F</sub>、I<sub>sp</sub>、F、ṁ；中间列为甲烷相对 RP-1 的差值", "比冲随 O/F 曲线与相对差值曲线，标出推力差变号点"],
        steps: ["拖动 O/F 看两种推进剂同步变化", "“分别设定”可各取最佳混合比比较", "解读条说明为何比冲高而推力接近"],
      }, () => env && env.ok && { inputs: { ...C }, outputs: env });
      const body = el("div");
      body.appendChild(el("div", { class: "group-title" }, "混合比"));
      ctl.link = UI.seg([{ value: true, label: "两者同 O/F" }, { value: false, label: "分别设定" }], linked, (x) => { linked = x; if (linked) { C.rp1_of = C.ch4_of; ctl.rp1.set(C.ch4_of); update(); } }, true);
      ctl.ch4 = UI.slider({ label: "液甲烷 O/F", min: 2.2, max: 4.0, value: C.ch4_of, step: 0.01, digits: 2, onChange: (x) => { C.ch4_of = x; if (linked) { C.rp1_of = x; ctl.rp1.set(x); } update(); } });
      ctl.rp1 = UI.slider({ label: "RP-1 O/F", min: 2.2, max: 4.0, value: C.rp1_of, step: 0.01, digits: 2, onChange: (x) => { C.rp1_of = x; if (linked) { C.ch4_of = x; ctl.ch4.set(x); } update(); } });
      [ctl.link.node, ctl.ch4.node, ctl.rp1.node].forEach((n) => body.appendChild(n));
      ctl.ch4.node.style.marginTop = "12px";
      body.appendChild(el("div", { class: "group-title", style: "margin-top:14px" }, "共同几何与环境"));
      ctl.ar = UI.slider({ label: "面积比", sym: "Aₑ/Aₜ", min: 2, max: 100, value: C.ar, log: true, digits: 2, onChange: (x) => { C.ar = x; update(); } });
      ctl.pa = UI.seg([{ value: 0, label: "真空" }, { value: 5000, label: "5 kPa" }, { value: 50000, label: "50 kPa" }, { value: 101325, label: "海平面" }], C.pa, (p) => { C.pa = p; update(); }, true);
      [ctl.ar.node, ctl.pa.node].forEach((n) => body.appendChild(n));
      body.appendChild(el("p", { class: "note", style: "margin-top:12px" }, "室压固定 10 MPa（RP-1 指定反应物方法域）。甲烷入口 120 K / 100 K、10 MPa 液体查表；RP-1 298.15 K / 90.170 K。"));
      const panel = el("div", { class: "panel" }); panel.appendChild(UI.card("输入", "", body));
      const res = el("div", { class: "results" });
      vs = el("div", { class: "card" }); banner = el("div", { class: "banner info" });
      isp = el("div", { class: "chart" }); setIsp = Chart.mount(isp);
      rel = el("div", { class: "chart" }); setRel = Chart.mount(rel);
      const g = el("div", { class: "grid-2" });
      const c1 = UI.card("比冲随 O/F", "", isp); c1.appendChild(el("div", { style: "padding-bottom:10px" }, Chart.legend([{ name: "液甲烷", color: "var(--ch4)" }, { name: "RP-1", color: "var(--rp1)" }])));
      const c2 = UI.card("相对差值", "甲烷 / RP-1 − 1", rel); c2.appendChild(el("div", { style: "padding-bottom:10px" }, Chart.legend([{ name: "比冲差", color: "var(--accent)" }, { name: "流量差", color: "var(--warn)" }, { name: "推力差", color: "var(--ink)" }])));
      g.appendChild(c1); g.appendChild(c2);
      [vs, banner, g].forEach((n) => res.appendChild(n));
      res.appendChild(el("p", { class: "note" }, "<b>方法</b> 两侧分别为连续液体查表甲烷与 CEA 指定 RP-1 替代物，同一 HP 平衡与冻结喷管求解；比较的是方法算例，不是两型发动机的实测排名。"));
      const work = el("div", { class: "work" }); work.appendChild(panel); work.appendChild(res); v.appendChild(work);
      Bus.on((w) => { if (w === "theme" && env) paint(); });
    },
    show() { update(); },
    cmd: () => `rocketperf.exe study propellants ${plain(C.ch4_of)} ${plain(C.rp1_of)} ${plain(C.ar)} ${plain(C.pa)} --text`,
  });
})();
