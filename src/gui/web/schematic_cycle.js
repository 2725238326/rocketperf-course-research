/* Cycle schematic on a fixed 1000×720 canvas. Positions were laid out so labels sit
 * in free space; staged combustion has one unavoidable crossing, drawn as an over-pass. */
const PX_PER_M = 350;
function cycleSchematic(c) {
  const gg = !c.inputs.staged_combustion, rp1 = c.feed === "rp1_assigned", B = c.balance, fuelC = rp1 ? COL.rp1 : COL.ch4;
  const vf = B.fuel_mass_flow_kg_per_s / c.density.fuel, vo = B.oxidizer_mass_flow_kg_per_s / c.density.oxidizer;
  const hMax = 270, hf = clamp(hMax * Math.min(1, vf / Math.max(vf, vo)), 196, hMax), ho = clamp(hMax * Math.min(1, vo / Math.max(vf, vo)), 196, hMax);
  const bottom = 290, fuelName = rp1 ? "RP-1" : "液甲烷", fuelT = rp1 ? "298 K" : `${c.inputs.fuel_temperature_k} K`;
  const rt = Math.sqrt(B.main_throat_area_m2 / Math.PI) * PX_PER_M, re = rt * Math.sqrt(c.inputs.main_area_ratio), rc = rt * Math.sqrt(3.2);
  let s = schematicDefs();
  const tanks = tank({ x: 40, y: bottom - ho, w: 104, h: ho, key: "ox_tank", fluid: "lox", name: "液氧箱",
      lines: [rp1 ? "90.17 K" : `${c.inputs.oxidizer_temperature_k} K`, `${fx(vo * 1000, 0)} L/s`] }) +
    tank({ x: 200, y: bottom - hf, w: 100, h: hf, key: "fuel_tank", fluid: rp1 ? "rp1" : "ch4", name: "燃料箱",
      lines: [`${fuelName}`, `${fuelT} · ${fx(vf * 1000, 0)} L/s`] });
  const eng = engine({ cx: 820, top: 130, lc: 92, rc, rt, re, ln: re * 1.55, plume: 118, pe: c.nozzle.pe, pa: c.inputs.ambient_pressure_pa, key: "engine",
    lines: ["主燃烧室", `${fx(c.chamber.t, 0)} K`, `${fx(c.inputs.chamber_pressure_pa / 1e6, 0)} MPa`] });
  // pipes underneath components, in drawing order (later pipes pass over earlier ones)
  let pipes = "";
  pipes += pipe([[250, bottom + 8], [250, 320], [436, 320]], fuelC, B.fuel_mass_flow_kg_per_s);
  pipes += pipe([[92, bottom + 8], [92, 590], [436, 590]], COL.lox, B.oxidizer_mass_flow_kg_per_s);
  // tees: the trunk from each pump carries the total, branches start at the tee point
  pipes += pipe([[540, 320], [540, 70], [850, 70], [850, 114]], fuelC, B.main_fuel_mass_flow_kg_per_s);
  pipes += pipe([[540, 320], [540, 458], [683, 458], [683, 470]], fuelC, B.branch_fuel_mass_flow_kg_per_s);
  pipes += pipe([[505, 320], [540, 320]], fuelC, B.fuel_mass_flow_kg_per_s);
  if (gg) {
    pipes += pipe([[700, 590], [940, 590], [940, 100], [892, 100], [892, 114]], COL.lox, B.main_oxidizer_mass_flow_kg_per_s);
    pipes += pipe([[700, 590], [700, 508], [689, 508]], COL.lox, B.branch_oxidizer_mass_flow_kg_per_s);
    pipes += pipe([[505, 590], [700, 590]], COL.lox, B.oxidizer_mass_flow_kg_per_s);
    pipes += pipe([[426, 455], [352, 455], [352, 515]], COL.gas, B.external_mass_flow_kg_per_s);
  } else {
    pipes += pipe([[505, 590], [700, 590], [700, 508], [689, 508]], COL.lox, B.branch_oxidizer_mass_flow_kg_per_s);
    pipes += pipe([[505, 438], [600, 438], [600, 100], [770, 100], [770, 114]], COL.gas, B.returned_mass_flow_kg_per_s);
  }
  const tee = (x, y, col) => el("circle", { cx: x, cy: y, r: 5, fill: col, stroke: "#fff", "stroke-width": 2 });
  pipes += tee(540, 320, fuelC) + (gg ? tee(700, 590, COL.lox) : "");
  pipes += pipe([[593, 494], [520, 494], [505, 482]], COL.gas, B.branch_mass_flow_kg_per_s);
  // branch exhaust nozzle (gas generator only), drawn to the same px/m scale
  let branch = "";
  if (gg) {
    const brt = Math.sqrt(B.branch_throat_area_m2 / Math.PI) * PX_PER_M, bre = brt * Math.sqrt(c.inputs.branch_area_ratio), y0 = 515;
    branch = `<g class="comp" data-key="branch">` +
      `<path class="flicker" d="M${352 - bre},${y0 + 30}L${352 - bre * 1.3},${y0 + 78}H${352 + bre * 1.3}L${352 + bre},${y0 + 30}Z" fill="url(#g-plume)"/>` +
      el("path", { d: `M${352 - brt * 1.6},${y0}H${352 + brt * 1.6}L${352 + brt},${y0 + 14}L${352 + bre},${y0 + 30}H${352 - bre}L${352 - brt},${y0 + 14}Z`,
        class: "outline", fill: "url(#g-copper)", stroke: "#5A3520", "stroke-width": 1.4 }) + "</g>" +
      label(334, 560, "外排喷管", `${fx(B.branch_thrust_n / 1e3, 2)} kN`, "end");
  }
  const parts = shaft(470, 320, 590) +
    pump({ cx: 470, cy: 320, r: 40, key: "fuel_pump", fluid: rp1 ? "rp1" : "ch4" }) +
    pump({ cx: 470, cy: 590, r: 40, key: "ox_pump", fluid: "lox" }) +
    turbine({ cx: 470, cy: 455, r: 42, key: "turbine", flanges: gg ? [[426, 455], [505, 482]] : [[505, 438], [505, 482]] }) +
    preburner({ x: 593, y: 494, key: "preburner" });
  const labels =
    label(308, 284, "燃料泵", `${fx(c.pump_w.fuel / 1e6, 2)} MW`) +
    label(470, 655, "氧泵", `${fx(c.pump_w.oxidizer / 1e6, 2)} MW · Δp ${fx((c.inputs.oxidizer_pump_outlet_pressure_pa - c.inputs.oxidizer_pump_inlet_pressure_pa) / 1e6, 0)} MPa`, "middle") +
    label(408, 398, "涡轮", `${fx(B.turbine_power_w / 1e6, 2)} MW · 出口 ${fx(c.turbine.out_pa / 1e6, 2)} MPa`, "end") +
    label(666, 540, gg ? "燃气发生器" : "富氧预燃室", `${fx(c.preburner.t, 0)} K · O/F ${c.inputs.preburner_oxidizer_fuel_ratio}`, "end") +
    el("text", { x: 820, y: eng.exitY + 136, "text-anchor": "middle", class: "name" }, `主路推力 ${fx(B.main_thrust_n / 1e3, 1)} kN`) +
    el("text", { x: 820, y: eng.exitY + 154, "text-anchor": "middle", class: "dim" }, `Dt ${fx(rt * 2 / PX_PER_M * 1000, 0)} · De ${fx(re * 2 / PX_PER_M * 1000, 0)} mm · ε ${c.inputs.main_area_ratio}`);
  const pills = pill(345, 320, `${fx(B.fuel_mass_flow_kg_per_s, 2)} kg/s`, fuelC) +
    pill(92, 450, `${fx(B.oxidizer_mass_flow_kg_per_s, 2)}`, COL.lox) +
    pill(680, 70, `${fx(B.main_fuel_mass_flow_kg_per_s, 2)} kg/s`, fuelC) +
    pill(612, 458, `${fx(B.branch_fuel_mass_flow_kg_per_s, 2)}`, fuelC) +
    pill(700, 552, `${fx(B.branch_oxidizer_mass_flow_kg_per_s, 2)}`, COL.lox) + pill(600, 590, `${fx(B.oxidizer_mass_flow_kg_per_s, 2)}`, COL.lox) +
    (gg ? pill(940, 380, `${fx(B.main_oxidizer_mass_flow_kg_per_s, 2)}`, COL.lox) + pill(352, 480, "外排", COL.gas)
        : pill(600, 300, `回流 ${fx(B.returned_mass_flow_kg_per_s, 2)}`, COL.gas)) +
    el("text", { x: 482, y: 528, class: "dim" }, `单轴 η ${c.inputs.shaft_efficiency}`);
  const legend = `<g transform="translate(560,676)">` +
    [[fuelC, "燃料"], [COL.lox, "液氧"], [COL.gas, "燃气"]].map(([col, t], i) =>
      el("line", { x1: i * 92, x2: i * 92 + 24, y1: 0, y2: 0, stroke: col, "stroke-width": 6 }) + el("text", { x: i * 92 + 30, y: 4.5, class: "sub" }, t)).join("") +
    el("text", { x: 0, y: 26, class: "dim" }, "线宽 ∝ √流量 · 喷管喉部/出口按计算尺寸绘制") + "</g>";
  return `<svg class="schematic" viewBox="0 0 1000 735" preserveAspectRatio="xMidYMid meet" role="img" aria-label="${gg ? "燃气发生器开式循环" : "富氧补燃循环"}流程图">` +
    s + pipes + tanks + eng.svg + branch + parts + labels + pills + legend + "</svg>";
}
