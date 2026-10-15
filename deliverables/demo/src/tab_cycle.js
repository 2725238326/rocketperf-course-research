/* Tab: cycle ledgers with a component schematic. Two scenarios, each closed on its own. */
TABS.push({ id: "cycle", title: "循环三本账", init() {
  const V = view("cycle"), P = {};
  const cases = DATA.cycles;
  const rail = card(V.rail, "循环三本账",
    `<p>共同输入：总供给 ${cases[0].inputs.total_mass_flow_kg_per_s} kg/s，主室 ${fx(cases[0].inputs.chamber_pressure_pa / 1e6, 0)} MPa，主喷管面积比 ${cases[0].inputs.main_area_ratio}，海平面背压。泵、预燃室、涡轮、主室在一次 C 调用里同时闭合质量、轴功、焓与元素。</p><p>两情景的燃料、O/F和泵压不同，不能用温度或比冲差单独评价循环优劣。</p>`);
  P.sel = seg(rail, "研究情景", [[0, "开式 · 朱雀三号一级"], [1, "补燃 · 长十乙一级"]], 0);
  const key = card(V.rail, "关键核对", "<p></p>");
  P.ev = evidence(V.rail);
  P.chain = chain(V.stage, "C 调用链");
  const row = kpiRow(V.stage, 4);
  P.k = [kpi(row, "整机推力", "主喷管 + 外排"), kpi(row, "整机比冲", "÷ 总供给"), kpi(row, "涡轮功率", "= 泵 + 辅助 / η轴"), kpi(row, "涡轮出口压力")];
  const grid = h("div", "cycle-stage"); V.stage.append(grid);
  const fig = figure(grid, { title: "", sub: "点击部件查看状态；线宽按质量流量缩放" });
  const side = h("div", "cycle-side"); grid.append(side);
  const detail = card(side, "", "", "detail"), ledgers = h("div"); side.append(ledgers);
  P.pinned = "engine";

  function details(c, k) {
    const B = c.balance, I = c.inputs, rp1 = c.feed === "rp1_assigned", MPa = (pa) => `${fx(pa / 1e6, 2)} MPa`;
    const map = {
      fuel_tank: ["燃料箱", [["推进剂", rp1 ? "RP-1（CEA 指定替代物）" : "液甲烷（CoolProp 单相表）"], ["入口温度", `${I.fuel_temperature_k} K`],
        ["密度", `${fx(c.density.fuel, 1)} kg/m³${rp1 ? "（假设值）" : ""}`], ["质量流量", `${fx(B.fuel_mass_flow_kg_per_s, 3)} kg/s`]]],
      ox_tank: ["液氧箱", [["入口温度", `${I.oxidizer_temperature_k} K`], ["密度", `${fx(c.density.oxidizer, 1)} kg/m³`], ["质量流量", `${fx(B.oxidizer_mass_flow_kg_per_s, 3)} kg/s`]]],
      fuel_pump: ["燃料泵", [["入口 → 出口", `${MPa(I.fuel_pump_inlet_pressure_pa)} → ${MPa(I.fuel_pump_outlet_pressure_pa)}`], ["效率", I.fuel_pump_efficiency],
        ["轴功率", `${fx(c.pump_w.fuel / 1e6, 3)} MW`], ["模型", "恒密度 Δp/(ρη)"]]],
      ox_pump: ["氧泵", [["入口 → 出口", `${MPa(I.oxidizer_pump_inlet_pressure_pa)} → ${MPa(I.oxidizer_pump_outlet_pressure_pa)}`], ["效率", I.oxidizer_pump_efficiency],
        ["轴功率", `${fx(c.pump_w.oxidizer / 1e6, 3)} MW`]]],
      preburner: [rp1 ? "富氧预燃室" : "燃气发生器", [["压力", MPa(I.preburner_pressure_pa)], ["O/F", I.preburner_oxidizer_fuel_ratio], ["HP 平衡温度", `${fx(c.preburner.t, 1)} K`],
        ["石墨活度 a<sub>C</sub>", sci(c.preburner.ac, 3)], ["流量", `${fx(B.branch_mass_flow_kg_per_s, 3)} kg/s`]]],
      turbine: ["涡轮", [["入口", `${fx(c.turbine.in_t, 0)} K · ${MPa(c.turbine.in_pa)}`], ["出口", `${fx(c.turbine.out_t, 0)} K · ${MPa(c.turbine.out_pa)}`],
        ["效率", I.turbine_efficiency], ["比功", `${fx(c.turbine.work_j_kg / 1e3, 1)} kJ/kg`], ["功率", `${fx(B.turbine_power_w / 1e6, 3)} MW`],
        [rp1 ? "出口压力" : "出口压力（输入）", rp1 ? `轴功反解，${c.turbine_pressure_iterations} 次二分` : "给定 0.8 MPa"]]],
      engine: ["主燃烧室与主喷管", [["HP 平衡温度", `${fx(c.chamber.t, 1)} K`], ["流量（含回流）", `${fx(B.main_mass_flow_kg_per_s, 3)} kg/s`],
        ["求得喉面积", `${fx(B.main_throat_area_m2 * 1e4, 1)} cm²`], ["c*", `${fx(c.nozzle.cstar, 1)} m/s`], ["C<sub>F</sub>（海平面）", fx(c.nozzle.cf, 4)],
        ["出口压力 / 马赫", `${kpa(c.nozzle.pe)} kPa / ${fx(c.nozzle.me, 2)}`], ["主路推力", `${fx(B.main_thrust_n / 1e3, 2)} kN`]]],
      branch: ["外排喷管", c.branch ? [["流量", `${fx(B.external_mass_flow_kg_per_s, 3)} kg/s`], ["面积比", I.branch_area_ratio], ["出口压力", `${kpa(c.branch.pe)} kPa`],
        ["轴向推力", `${fx(B.branch_thrust_n / 1e3, 3)} kN`], ["占整机", `${fx((B.branch_thrust_n / B.total_thrust_n) * 100, 2)}%`]] : []],
    };
    return map[k];
  }
  function showDetail(c, k) {
    const [title, rows] = details(c, k);
    detail.innerHTML = `<h3>${title}<span class="muted">点击其他部件切换</span></h3><div class="ev"><table>${rows.map(([a, b]) => `<tr><td>${a}</td><td>${b}</td></tr>`).join("")}</table></div>`;
  }
  function ledger(c) {
    const B = c.balance, gg = !c.inputs.staged_combustion, tot = c.inputs.total_mass_flow_kg_per_s, W = (w) => `${fx(w / 1e6, 3)} MW`;
    const bar = (parts) => `<div class="bar">${parts.map(([v, col, t]) => `<span style="width:${(100 * v).toFixed(2)}%;background:${col}" title="${t}"></span>`).join("")}</div>`;
    const shaftIn = B.turbine_power_w * c.inputs.shaft_efficiency, shaftOut = B.pump_power_w + c.inputs.auxiliary_power_w;
    ledgers.innerHTML =
      `<div class="ledger"><h4>质量账<span>残差 ${sci(B.mass_relative_residual)}</span></h4><div class="bal">` +
      `<span>供给</span>${bar([[B.fuel_mass_flow_kg_per_s / tot, "var(--" + (c.feed === "rp1_assigned" ? "rp1" : "ch4") + ")", "燃料"], [B.oxidizer_mass_flow_kg_per_s / tot, "var(--lox)", "液氧"]])}` +
      `<span>排出</span>${bar([[(B.main_mass_flow_kg_per_s) / tot, "#C2412D", "主喷管"], [B.external_mass_flow_kg_per_s / tot, "#F2A65A", "外排"]])}</div>` +
      `<div class="bal-note">主喷管 <b>${fx(B.main_mass_flow_kg_per_s, 3)}</b>${gg ? ` + 外排 <b>${fx(B.external_mass_flow_kg_per_s, 3)}</b>` : `（含回流 <b>${fx(B.returned_mass_flow_kg_per_s, 3)}</b>）`} = <b>${fx(tot, 3)}</b> kg/s</div></div>` +
      `<div class="ledger"><h4>轴功账<span>残差 ${sci(B.shaft_residual_w)} W</span></h4><div class="bal">` +
      `<span>涡轮×η</span>${bar([[1, "#66758C", "涡轮×η轴"]])}<span>负载</span>${bar([[c.pump_w.fuel / shaftIn, "var(--" + (c.feed === "rp1_assigned" ? "rp1" : "ch4") + ")", "燃料泵"], [c.pump_w.oxidizer / shaftIn, "var(--lox)", "氧泵"], [c.inputs.auxiliary_power_w / shaftIn, "#B9C2D0", "辅助"]])}</div>` +
      `<div class="bal-note"><b>${W(shaftIn)}</b> = 燃料泵 <b>${W(c.pump_w.fuel)}</b> + 氧泵 <b>${W(c.pump_w.oxidizer)}</b> + 辅助 <b>${W(c.inputs.auxiliary_power_w)}</b></div></div>` +
      `<div class="ledger"><h4>焓账（Q = 0）<span>残差 ${fx(B.energy_residual_w, 3)} W</span></h4>` +
      `<div class="bal-note">入口焓流 <b>${W(B.inlet_enthalpy_rate_w)}</b> − 出口总焓流 <b>${W(B.exit_total_enthalpy_rate_w)}</b> = 辅助 + 机械损失 <b>${W(c.inputs.auxiliary_power_w + B.mechanical_loss_w)}</b></div></div>` +
      `<div class="ledger"><h4>元素账<span>最大 ${sci(Math.max(...c.element_residual.map(Math.abs)))}</span></h4>` +
      `<div class="bal-note">出口 C / H / O 相对残差 <b>${c.element_residual.map((x) => sci(x, 2)).join(" / ")}</b></div></div>`;
    return shaftOut;
  }
  function render() {
    const c = cases[P.sel.get()], B = c.balance, gg = !c.inputs.staged_combustion;
    fig.el.querySelector("h3").textContent = gg ? "燃气发生器开式循环（朱雀三号一级背景）" : "富氧补燃循环（长征十号乙一级背景）";
    fig.body.innerHTML = cycleSchematic(c);
    const svg = fig.body.querySelector("svg");
    svg.querySelectorAll(".comp").forEach((g) => {
      const k = g.dataset.key;
      g.addEventListener("pointermove", (e) => { const [t, rows] = details(c, k); showTip(tipTable(t, rows), e.clientX, e.clientY); });
      g.addEventListener("pointerleave", hideTip);
      g.addEventListener("click", () => { P.pinned = k; svg.querySelectorAll(".comp").forEach((x) => x.classList.toggle("sel", x === g)); showDetail(c, k); });
      if (k === P.pinned) g.classList.add("sel");
    });
    if (!details(c, P.pinned) || !details(c, P.pinned)[1].length) P.pinned = "engine";
    showDetail(c, P.pinned);
    ledger(c);
    P.k[0].set({ v: B.total_thrust_n / 1e3, d: 2, unit: "kN", foot: `主路 <b>${fx(B.main_thrust_n / 1e3, 2)}</b> + 外排 <b>${fx(B.branch_thrust_n / 1e3, 3)}</b>` });
    P.k[1].set({ v: B.engine_specific_impulse_s, d: 2, unit: "s", foot: `总供给 <b>${fx(c.inputs.total_mass_flow_kg_per_s, 0)}</b> kg/s，海平面` });
    P.k[2].set({ v: B.turbine_power_w / 1e6, d: 3, unit: "MW", foot: `泵 <b>${fx(B.pump_power_w / 1e6, 3)}</b> + 辅助 <b>${fx(c.inputs.auxiliary_power_w / 1e6, 2)}</b>，η轴 ${c.inputs.shaft_efficiency}` });
    P.k[3].set({ v: c.turbine.out_pa / 1e6, d: 2, unit: "MPa", foot: gg ? "给定外排背压" : `${badge("ok", "≥ 下限")}回流注入需 <b>${fx((c.inputs.chamber_pressure_pa + c.inputs.return_pressure_drop_pa) / 1e6, 2)}</b> MPa` });
    P.chain.set([{ name: "泵", val: `2 × 恒密度` }, { name: gg ? "发生器 HP" : "预燃室 HP", val: `${fx(c.preburner.t, 0)} K` },
      { name: "涡轮冻结膨胀", val: gg ? "给定出口" : `出口压力二分 ${c.turbine_pressure_iterations} 次` },
      { name: gg ? "外排喷管" : "回流混合", val: gg ? `${fx(B.external_mass_flow_kg_per_s, 2)} kg/s` : `${fx(B.returned_mass_flow_kg_per_s, 1)} kg/s` },
      { name: "主室 HP", val: `${fx(c.chamber.t, 0)} K` }, { name: "主喷管", val: `喉 ${fx(B.main_throat_area_m2 * 1e4, 1)} cm²` },
      { name: "三本账闭合", val: `|ΔQ| ${fx(Math.abs(B.energy_residual_w), 2)} W` }]);
    key.innerHTML = `<h2>关键核对</h2><p>` + (gg
      ? `外排 <b>${fx(B.external_mass_flow_kg_per_s, 3)} kg/s</b> 经独立喷管仍贡献 <b>${fx(B.branch_thrust_n / 1e3, 3)} kN</b>，占整机 ${fx((B.branch_thrust_n / B.total_thrust_n) * 100, 2)}%，漏记即低估推力和比冲。发生器 O/F 1.0，石墨活度 ${fx(c.preburner.ac, 3)} &lt; 1，仍在气相域内。`
      : `轴功平衡反解涡轮出口 <b>${fx(c.turbine.out_pa / 1e6, 2)} MPa</b>，高于回流注入主室所需 <b>${fx((c.inputs.chamber_pressure_pa + c.inputs.return_pressure_drop_pa) / 1e6, 2)} MPa</b>：功率账在注入约束内成立。RP-1 为指定替代物，燃料密度为假设值。`) + "</p>";
    P.ev.set([["轴功残差", `${sci(B.shaft_residual_w)} W`], ["焓残差", `${fx(B.energy_residual_w, 3)} W`], ["质量相对残差", sci(B.mass_relative_residual)],
      ["元素最大残差", sci(Math.max(...c.element_residual.map(Math.abs)))]], command("cycle", { case: c.case }));
  }
  P.sel.on(render);
  render();
} });
