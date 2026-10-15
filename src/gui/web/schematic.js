"use strict";
/* Engine schematics drawn from C results: nozzle contour (radius = sqrt(Ae/At))
 * coloured by the computed station temperatures, and the two cycle topologies. */
const Schem = (() => {
  const HEAT = [[0, [255, 246, 214]], [0.25, [255, 196, 87]], [0.5, [244, 114, 54]], [0.75, [190, 52, 85]], [1, [70, 60, 140]]];
  function heat(f) {
    for (let i = 1; i < HEAT.length; i++) {
      if (f <= HEAT[i][0]) {
        const [a, ca] = HEAT[i - 1], [b, cb] = HEAT[i], k = (f - a) / (b - a);
        return `rgb(${ca.map((c, j) => Math.round(c + (cb[j] - c) * k)).join(",")})`;
      }
    }
    return `rgb(${HEAT[HEAT.length - 1][1].join(",")})`;
  }

  /* r.profile: {ar,p,t,mach,u}; regime name and pa from the nozzle command. */
  function nozzle(host, r, onHover) {
    const w = host.clientWidth || 640, h = host.clientHeight || 300;
    host.innerHTML = "";
    const s = svg("svg", { class: "schem", viewBox: `0 0 ${w} ${h}` }, host);
    const pr = r.profile, eps = r.ar, cy = h * 0.47;
    const exitR = Math.min(h * 0.3, 30 * Math.sqrt(eps)), rt = exitR / Math.sqrt(eps);
    const rc = Math.min(rt * 2.2, h * 0.3), lc = Math.max(48, rc * 1.6), lconv = Math.max(24, (rc - rt) * 1.3);
    const ldiv = Math.min(w * 0.42, Math.max(60, (exitR - rt) / Math.tan(15 * Math.PI / 180) * 0.72));
    const x0 = 24, xt = x0 + lc + lconv, xe = xt + ldiv;
    const xOf = (a) => xt + ldiv * Math.pow((Math.sqrt(a) - 1) / (Math.sqrt(eps) - 1 || 1), 0.72);
    const tmax = r.chamber.gas.t, tmin = Math.min(...pr.t);
    const defs = svg("defs", null, s), grad = svg("linearGradient", { id: "nz-heat", x1: x0, x2: xe, y1: 0, y2: 0, gradientUnits: "userSpaceOnUse" }, defs);
    const stop = (x, t) => svg("stop", { offset: clamp((x - x0) / (xe - x0), 0, 1), "stop-color": heat(clamp((tmax - t) / (tmax - tmin || 1), 0, 1)) }, grad);
    stop(x0, tmax); stop(xt - lconv * 0.4, tmax);
    pr.ar.forEach((a, i) => stop(xOf(a), pr.t[i]));
    const upper = [[x0, cy - rc], [x0 + lc, cy - rc]];
    for (let k = 1; k <= 10; k++) { const f = k / 10; upper.push([x0 + lc + lconv * f, cy - (rc - (rc - rt) * (0.5 - 0.5 * Math.cos(Math.PI * f)))]); }
    for (let k = 1; k <= 24; k++) { const a = 1 + (eps - 1) * (k / 24) ** 1.6; upper.push([xOf(a), cy - rt * Math.sqrt(a)]); }
    const lower = upper.map(([x, y]) => [x, 2 * cy - y]).reverse();
    const pts = (arr) => arr.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
    const pe = r.ideal.exit.gas.p, pa = r.pa, regime = r.regime.name;
    const plumeLen = Math.min(w - xe - 16, 220), spread = pa === 0 ? 1.9 : pe > pa ? 1 + 0.6 * Math.min(1, Math.log10(pe / pa + 1)) : 0.62;
    const pg = svg("linearGradient", { id: "nz-plume", x1: 0, x2: 1, y1: 0, y2: 0 }, defs);
    svg("stop", { offset: 0, "stop-color": heat(0.8), "stop-opacity": 0.55 }, pg); svg("stop", { offset: 1, "stop-color": heat(0.9), "stop-opacity": 0 }, pg);
    const ey = exitR, py = Math.min(ey * spread, h * 0.44);
    svg("path", { d: `M${xe},${cy - ey} C${xe + plumeLen * 0.35},${cy - py} ${xe + plumeLen * 0.7},${cy - py} ${xe + plumeLen},${cy - py * 0.9} L${xe + plumeLen},${cy + py * 0.9} C${xe + plumeLen * 0.7},${cy + py} ${xe + plumeLen * 0.35},${cy + py} ${xe},${cy + ey} Z`, fill: "url(#nz-plume)" }, s);
    if (pa > 0 && pe < pa) for (let k = 0; k < 3; k++) {
      const x = xe + 18 + k * plumeLen * 0.26, d = ey * spread * (0.95 - k * 0.12);
      svg("path", { d: `M${x},${cy - d} L${x + plumeLen * 0.13},${cy} L${x},${cy + d}`, fill: "none", stroke: css("--bad"), "stroke-width": 1.2, opacity: 0.55 - k * 0.12 }, s);
    }
    svg("polygon", { points: pts([...upper, ...lower]), fill: "url(#nz-heat)" }, s);
    const wall = (arr, sign) => pts([...arr, ...arr.slice().reverse().map(([x, y]) => [x, y + sign * 5])]);
    svg("polygon", { class: "wall", points: wall(upper, -1) }, s);
    svg("polygon", { class: "wall", points: wall(lower.slice().reverse(), 1) }, s);
    svg("line", { x1: x0 - 4, x2: xe + plumeLen, y1: cy, y2: cy, stroke: css("--ink-3"), "stroke-dasharray": "6 5", opacity: 0.5 }, s);
    if (finite(r.regime.separation_ar) && r.regime.separation_ar < eps) {
      const xs = xOf(r.regime.separation_ar), ys = cy - rt * Math.sqrt(r.regime.separation_ar);
      svg("line", { x1: xs, x2: xs, y1: ys - 14, y2: 2 * cy - ys + 14, stroke: css("--bad"), "stroke-width": 2, "stroke-dasharray": "4 3" }, s);
      svg("text", { x: xs, y: ys - 20, "text-anchor": "middle", style: `fill:${css("--bad")};font-weight:600` }, s).textContent = `p = 0.4·pₐ 参考位置 ε ${F.n(r.regime.separation_ar, 1)}`;
    }
    const label = (x, y, a, b, anchor) => {
      const t = svg("text", { x, y, "text-anchor": anchor || "middle" }, s);
      svg("tspan", { class: "lab", x, dy: 0 }, t).textContent = a;
      svg("tspan", { class: "val", x, dy: 15 }, t).textContent = b;
    };
    const ex = r.ideal.exit, th = r.ideal.throat;
    label(x0 + lc / 2, cy - rc - 26, "燃烧室", `${F.n(r.chamber.gas.t, 0)} K · ${F.mpa(r.chamber.gas.p)} MPa`);
    label(xt, cy + Math.max(rt, rc * 0.5) + 26, "喉部 Ma 1", `${F.n(th.gas.t, 0)} K · ${F.mpa(th.gas.p)} MPa`);
    label(xe, cy + exitR + 24, `出口 ε ${F.g(eps, 3)}`, `Ma ${F.n(ex.mach, 2)} · ${F.kpa(ex.gas.p)} kPa`);
    label(w - 12, 18, pa === 0 ? "真空" : `环境 ${F.ambient(pa)}`,
      pa === 0 ? "欠膨胀" : pe >= pa ? "pₑ ≥ pₐ 附着" : `pₑ/pₐ = ${F.n(pe / pa, 3)}`, "end");
    const hit = svg("rect", { x: xt, y: cy - exitR - 6, width: xe - xt, height: 2 * exitR + 12, fill: "transparent" }, s);
    const cursor = svg("line", { y1: cy - exitR - 6, y2: cy + exitR + 6, stroke: css("--ink"), "stroke-width": 1, visibility: "hidden" }, s);
    hit.addEventListener("mousemove", (ev) => {
      const rect = s.getBoundingClientRect(), px = (ev.clientX - rect.left) * (w / rect.width);
      let best = 0, bd = Infinity;
      pr.ar.forEach((a, i) => { const d = Math.abs(xOf(a) - px); if (d < bd) { bd = d; best = i; } });
      cursor.setAttribute("x1", xOf(pr.ar[best])); cursor.setAttribute("x2", xOf(pr.ar[best])); cursor.setAttribute("visibility", "visible");
      onHover && onHover(best, ev);
    });
    hit.addEventListener("mouseleave", () => { cursor.setAttribute("visibility", "hidden"); hideTip(); });
    return regime;
  }

  /* Cycle topology. staged=false: gas generator with external dump nozzle;
   * staged=true: oxidizer-rich preburner, all turbine gas returns to the chamber. */
  function cycle(host, r) {
    const W = 660, H = 440, staged = r.case.staged, b = r.balance;
    host.innerHTML = "";
    const s = svg("svg", { class: "schem", viewBox: `0 0 ${W} ${H}` }, host);
    const total = b.fuel_flow + b.oxidizer_flow, wid = (q) => 3 + 11 * Math.sqrt(Math.max(q, 0) / total);
    const fuelC = r.case.feed === "rp1_assigned" ? css("--rp1") : css("--ch4"), oxC = css("--ox"), hotC = css("--hot");
    const pipe = (d, color, q, off) => {
      const width = wid(q);
      svg("path", { class: "pipe", d, stroke: css("--panel"), "stroke-width": width + 5 }, s);
      svg("path", { class: `pipe${off ? " off" : ""}`, d, stroke: color, "stroke-width": width }, s);
      if (!off && q > 0) svg("path", { class: "flow", d, "stroke-width": Math.max(1.4, width / 3.2) }, s);
    };
    const text = (x, y, a, cls, anchor) => { const t = svg("text", { x, y, class: cls || "", "text-anchor": anchor || "middle" }, s); t.textContent = a; return t; };
    const kv = (x, y, k, v2, anchor) => { text(x, y, k, "lab", anchor); text(x, y + 15, v2, "val", anchor); };
    const fuelName = r.case.feed === "rp1_assigned" ? "RP-1" : "液甲烷";
    pipe("M80,186 L132,186 L132,258 L178,258", fuelC, b.fuel_flow);
    pipe("M580,186 L528,186 L528,258 L482,258", oxC, b.oxidizer_flow);
    pipe("M178,258 L200,258 L200,206 L320,206", fuelC, b.branch_fuel_flow);
    pipe("M482,258 L460,258 L460,206 L340,206", oxC, b.branch_oxidizer_flow);
    pipe("M206,284 L206,352 L292,352", fuelC, b.fuel_flow - b.branch_fuel_flow);
    pipe("M454,284 L454,352 L368,352", oxC, b.oxidizer_flow - b.branch_oxidizer_flow, b.oxidizer_flow - b.branch_oxidizer_flow < 1e-9);
    pipe("M330,152 L330,120 L310,120 L310,102", hotC, b.branch_flow);
    if (staged) pipe("M350,102 L350,86 L410,86 L410,310 L344,310 L344,326", hotC, b.returned_flow);
    else pipe("M350,102 L350,86 L600,86 L600,236", hotC, b.external_flow);
    svg("rect", { class: "box tank-f", x: 26, y: 140, width: 54, height: 92, rx: 22 }, s);
    svg("rect", { class: "box tank-o", x: 580, y: 140, width: 54, height: 92, rx: 22 }, s);
    text(53, 132, fuelName); text(607, 132, "液氧");
    svg("line", { class: "shaft", x1: 206, x2: 454, y1: 258, y2: 258 }, s);
    svg("circle", { class: "box", cx: 206, cy: 258, r: 26, style: `stroke:${fuelC}` }, s);
    svg("circle", { class: "box", cx: 454, cy: 258, r: 26, style: `stroke:${oxC}` }, s);
    text(206, 262, "燃料泵"); text(454, 262, "氧泵");
    svg("polygon", { class: "box hot", points: "296,48 364,40 364,112 296,104" }, s);
    text(330, 80, "涡轮");
    svg("rect", { class: `box hot`, x: 296, y: 152, width: 68, height: 64, rx: 10 }, s);
    text(330, 172, staged ? "富氧预燃室" : "燃气发生器"); text(330, 190, `${F.n(r.preburner.gas.t, 0)} K`, "val"); text(330, 206, `O/F ${F.n(r.inputs.preburner_oxidizer_fuel_ratio, 2)}`, "lab");
    svg("line", { class: "shaft", x1: 330, x2: 330, y1: 112, y2: 258, style: "stroke-dasharray:2 5" }, s);
    svg("rect", { class: "box hot", x: 292, y: 326, width: 76, height: 50, rx: 12 }, s);
    text(330, 356, "主燃烧室");
    svg("path", { class: "box hot", d: "M306,376 L318,392 L300,432 L360,432 L342,392 L354,376 Z" }, s);
    if (!staged) { svg("path", { class: "box hot", d: "M592,236 L608,236 L620,272 L580,272 Z" }, s); text(600, 290, "外排喷管", "lab"); }
    const t = r.turbine;
    kv(206, 304, "泵功率", `${F.mw(r.pumps.fuel_w)} MW`); kv(454, 304, "泵功率", `${F.mw(r.pumps.oxidizer_w)} MW`);
    kv(250, 52, "涡轮入口", `${F.n(t.in_t, 0)} K · ${F.mpa(t.in_p)} MPa`, "end");
    kv(250, 86, "涡轮出口", `${F.n(t.out_t, 0)} K · ${F.mpa(t.out_p)} MPa`, "end");
    kv(staged ? 418 : 480, staged ? 140 : 70, staged ? "回流主室" : "外排燃气", `${F.n(staged ? b.returned_flow : b.external_flow, 2)} kg/s`, "start");
    kv(200, 196, "燃料支路", `${F.n(b.branch_fuel_flow, 2)} kg/s`, "end");
    kv(470, 196, "氧支路", `${F.n(b.branch_oxidizer_flow, 2)} kg/s`, "start");
    kv(120, 372, "主路燃料", `${F.n(b.fuel_flow - b.branch_fuel_flow, 2)} kg/s`, "start");
    kv(540, 372, "主路氧", `${F.n(b.oxidizer_flow - b.branch_oxidizer_flow, 2)} kg/s`, "end");
    kv(392, 410, "主室", `${F.n(r.chamber.gas.t, 0)} K · ${F.mpa(r.inputs.chamber_pressure_pa)} MPa`, "start");
  }
  return { nozzle, cycle };
})();
