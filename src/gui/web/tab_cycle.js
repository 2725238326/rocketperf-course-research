"use strict";
/* Tab: engine cycle ledgers with the component schematic, solved live by the C core.
 * All five bundled vehicle cases; any editable input re-solves the whole engine. */
const CYCLE_CASES = [
  ["cases/vehicles/zq3_y1_stage1.ini", "朱雀三号一级", "开式"], ["cases/vehicles/zq3_y1_stage2.ini", "朱雀三号二级", "开式"],
  ["cases/vehicles/cz10b_first_stage1.ini", "长十乙一级", "补燃"], ["cases/vehicles/cz10b_first_stage2.ini", "长十乙二级", "开式 · 待判"],
  ["cases/vehicles/cz10b_first_stage2_orsc.ini", "长十乙二级", "补燃 · 待判"]];
const CYCLE_FIELDS = [
  ["整机", [["total_mass_flow_kg_per_s", "总流量", "kg/s", 1], ["overall_oxidizer_fuel_ratio", "总体 O/F", "", 1],
    ["chamber_pressure_pa", "主室压力", "MPa", 1e6], ["main_area_ratio", "主喷管面积比", "", 1], ["ambient_pressure_pa", "环境压力", "kPa", 1e3]]],
  ["预燃室 / 发生器", [["preburner_pressure_pa", "压力", "MPa", 1e6], ["preburner_oxidizer_fuel_ratio", "O/F", "", 1]]],
  ["涡轮泵", [["turbine_efficiency", "涡轮效率", "", 1], ["turbine_outlet_pressure_pa", "涡轮出口压力", "MPa", 1e6, "gg"], ["shaft_efficiency", "轴效率", "", 1],
    ["fuel_pump_outlet_pressure_pa", "燃料泵出口", "MPa", 1e6], ["oxidizer_pump_outlet_pressure_pa", "氧泵出口", "MPa", 1e6],
    ["fuel_pump_efficiency", "燃料泵效率", "", 1], ["oxidizer_pump_efficiency", "氧泵效率", "", 1]]],
  ["管路", [["return_pressure_drop_pa", "回流压降", "MPa", 1e6, "sc"], ["branch_area_ratio", "外排喷管面积比", "", 1, "gg"]]]];
const CYCLE_SWEEPS = [["preburner_oxidizer_fuel_ratio", "预燃室 O/F", 0.6, 1.4], ["chamber_pressure_pa", "主室压力", 0.7, 1.2],
  ["turbine_efficiency", "涡轮效率", 0.75, 1.25], ["main_area_ratio", "主喷管面积比", 0.5, 2]];

/* Map the bridge reply onto the field names the schematic and ledgers were drawn for. */
function cycleModel(r) {
  const b = r.balance, i = r.inputs, f = r.fixed, staged = r.case.staged;
  return {
    feed: r.case.feed, staged,
    inputs: { ...i, staged_combustion: staged, fuel_temperature_k: f.fuel_temperature_k, oxidizer_temperature_k: f.oxidizer_temperature_k,
      fuel_pump_inlet_pressure_pa: f.fuel_pump_inlet_pressure_pa, oxidizer_pump_inlet_pressure_pa: f.oxidizer_pump_inlet_pressure_pa },
    density: { fuel: f.fuel_density, oxidizer: f.oxidizer_density },
    pump_w: { fuel: r.pumps.fuel_w, oxidizer: r.pumps.oxidizer_w },
    preburner: { t: r.preburner.gas.t, ac: r.preburner.graphite_activity },
    chamber: { t: r.chamber.gas.t, ac: r.chamber.graphite_activity },
    turbine: { in_t: r.turbine.in_t, in_pa: r.turbine.in_p, out_t: r.turbine.out_t, out_pa: r.turbine.out_p, work_j_kg: r.turbine.work },
    nozzle: { cstar: r.main_nozzle.cstar, cf: r.main_nozzle.cf, pe: r.main_nozzle.pe, me: r.main_nozzle.me },
    branch: r.branch_nozzle,
    element_residual: r.diagnostics.exit_element_residuals || [r.diagnostics.exit_element_residual],
    turbine_pressure_iterations: r.diagnostics.turbine_pressure_iterations,
    balance: { fuel_mass_flow_kg_per_s: b.fuel_flow, oxidizer_mass_flow_kg_per_s: b.oxidizer_flow, branch_mass_flow_kg_per_s: b.branch_flow,
      branch_fuel_mass_flow_kg_per_s: b.branch_fuel_flow, branch_oxidizer_mass_flow_kg_per_s: b.branch_oxidizer_flow,
      returned_mass_flow_kg_per_s: b.returned_flow, external_mass_flow_kg_per_s: b.external_flow, main_mass_flow_kg_per_s: b.main_flow,
      main_fuel_mass_flow_kg_per_s: b.main_fuel_flow, main_oxidizer_mass_flow_kg_per_s: b.main_oxidizer_flow,
      turbine_power_w: b.turbine_power, pump_power_w: b.pump_power, mechanical_loss_w: b.mechanical_loss,
      inlet_enthalpy_rate_w: b.inlet_enthalpy_rate, exit_total_enthalpy_rate_w: b.exit_enthalpy_rate,
      main_throat_area_m2: b.main_throat_area, branch_throat_area_m2: b.branch_throat_area,
      main_thrust_n: b.main_thrust, branch_thrust_n: b.branch_thrust, total_thrust_n: b.total_thrust, engine_specific_impulse_s: b.isp,
      mass_relative_residual: b.mass_relative, shaft_residual_w: b.shaft_residual, energy_residual_w: b.energy_residual },
  };
}

TABS.push({ id: "cycle", title: "循环三本账", init() {
  const V = view("cycle"), P = { file: CYCLE_CASES[0][0], over: {}, base: null, env: null, sweepField: CYCLE_SWEEPS[0][0], sweep: null, pinned: "engine" };
  const c1 = card(V.rail, "循环三本账", `<p>泵、预燃室/发生器、涡轮、主室在一次 C 调用里同时闭合质量、轴功、焓与元素。算例输入为研究假设，型号名称只表示构型背景。</p>`);
  const list = h("div", "cases"); c1.append(list);
  CYCLE_CASES.forEach(([file, name, kind]) => {
    const b = h("button", "", `<span>${name}</span>${badge(kind.includes("待判") ? "warn" : "ok", kind)}`); b.type = "button"; b.dataset.file = file;
    b.addEventListener("click", () => select(file)); list.append(b);
  });
  P.key = card(V.rail, "关键核对", "<p></p>");
  const inputs = card(V.rail, "可编辑输入", `<p class="muted" style="font-size:0.84rem">改值后回车即重解整机；改过的项变蓝。</p><div class="fields"></div><button type="button" class="linkbtn">恢复算例原值</button>`);
  P.form = inputs.querySelector(".fields"); P.reset = inputs.querySelector(".linkbtn");
  P.reset.addEventListener("click", () => { P.over = {}; buildForm(); solve(); });
  P.ev = evidence(V.rail);
  P.chain = chain(V.stage, "C 调用链");
  const row = kpiRow(V.stage, 4);
  P.k = [kpi(row, "整机推力", "主喷管 + 外排"), kpi(row, "整机比冲", "÷ 总供给"), kpi(row, "涡轮功率", "= (泵 + 辅助) / η轴"), kpi(row, "涡轮出口压力")];
  const grid = h("div", "cycle-stage"); V.stage.append(grid);
  const fig = figure(grid, { title: "", sub: "点击部件查看状态；线宽按质量流量缩放" });
  const side = h("div", "cycle-side"); grid.append(side);
  const detail = card(side, "", "", "detail"), ledgers = h("div"); side.append(ledgers);
  const sw = figure(V.stage, { title: "单参数扫描：整机比冲", sub: "每点独立求解整机 · 灰区为 C 拒算 · 悬停看预燃室温度与推力" });
  sw.el.style.flex = "0 0 12.5rem";
  const pick = h("div", "sweep-pick"); sw.head.append(pick);
  CYCLE_SWEEPS.forEach(([key, label]) => {
    const b = h("button", "", label); b.type = "button"; b.dataset.key = key;
    b.addEventListener("click", () => { P.sweepField = key; paintPick(); sweep(); }); pick.append(b);
  });
  const paintPick = () => pick.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.key === P.sweepField)));
  paintPick();

  function details(c, k) {
    const B = c.balance, I = c.inputs, rp1 = c.feed === "rp1_assigned", MPa = (pa) => `${fx(pa / 1e6, 2)} MPa`;
    const map = {
      fuel_tank: ["燃料箱", [["推进剂", rp1 ? "RP-1（CEA 指定替代物）" : "液甲烷（CoolProp 单相表）"], ["入口温度", `${fx(I.fuel_temperature_k, 2)} K`],
        ["密度", `${fx(c.density.fuel, 1)} kg/m³${rp1 ? "（假设值）" : ""}`], ["质量流量", `${fx(B.fuel_mass_flow_kg_per_s, 3)} kg/s`]]],
      ox_tank: ["液氧箱", [["入口温度", `${fx(I.oxidizer_temperature_k, 2)} K`], ["密度", `${fx(c.density.oxidizer, 1)} kg/m³`], ["质量流量", `${fx(B.oxidizer_mass_flow_kg_per_s, 3)} kg/s`]]],
      fuel_pump: ["燃料泵", [["入口 → 出口", `${MPa(I.fuel_pump_inlet_pressure_pa)} → ${MPa(I.fuel_pump_outlet_pressure_pa)}`], ["效率", I.fuel_pump_efficiency],
        ["轴功率", `${fx(c.pump_w.fuel / 1e6, 3)} MW`], ["模型", "恒密度 Δp/(ρη)"]]],
      ox_pump: ["氧泵", [["入口 → 出口", `${MPa(I.oxidizer_pump_inlet_pressure_pa)} → ${MPa(I.oxidizer_pump_outlet_pressure_pa)}`], ["效率", I.oxidizer_pump_efficiency],
        ["轴功率", `${fx(c.pump_w.oxidizer / 1e6, 3)} MW`]]],
      preburner: [c.staged ? "富氧预燃室" : "燃气发生器", [["压力", MPa(I.preburner_pressure_pa)], ["O/F", fx(I.preburner_oxidizer_fuel_ratio, 2)], ["HP 平衡温度", `${fx(c.preburner.t, 1)} K`],
        ["石墨活度 a<sub>C</sub>", sci(c.preburner.ac, 3)], ["流量", `${fx(B.branch_mass_flow_kg_per_s, 3)} kg/s`]]],
      turbine: ["涡轮", [["入口", `${fx(c.turbine.in_t, 0)} K · ${MPa(c.turbine.in_pa)}`], ["出口", `${fx(c.turbine.out_t, 0)} K · ${MPa(c.turbine.out_pa)}`],
        ["效率", I.turbine_efficiency], ["比功", `${fx(c.turbine.work_j_kg / 1e3, 1)} kJ/kg`], ["功率", `${fx(B.turbine_power_w / 1e6, 3)} MW`],
        ["出口压力", c.staged ? `轴功反解，${c.turbine_pressure_iterations} 次二分` : `给定 ${MPa(I.turbine_outlet_pressure_pa)}`]]],
      engine: ["主燃烧室与主喷管", [["HP 平衡温度", `${fx(c.chamber.t, 1)} K`], ["流量（含回流）", `${fx(B.main_mass_flow_kg_per_s, 3)} kg/s`],
        ["求得喉面积", `${fx(B.main_throat_area_m2 * 1e4, 1)} cm²`], ["c*", `${fx(c.nozzle.cstar, 1)} m/s`], [`C<sub>F</sub>（${envName(I.ambient_pressure_pa)}）`, fx(c.nozzle.cf, 4)],
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
    const B = c.balance, gg = !c.staged, tot = c.inputs.total_mass_flow_kg_per_s, W = (w) => `${fx(w / 1e6, 3)} MW`;
    const fuelVar = `var(--${c.feed === "rp1_assigned" ? "rp1" : "ch4"})`;
    const bar = (parts) => `<div class="bar">${parts.map(([v, col, t]) => `<span style="width:${(100 * v).toFixed(2)}%;background:${col}" title="${t}"></span>`).join("")}</div>`;
    const shaftIn = B.turbine_power_w * c.inputs.shaft_efficiency;
    ledgers.innerHTML =
      `<div class="ledger"><h4>质量账<span>残差 ${sci(B.mass_relative_residual)}</span></h4><div class="bal">` +
      `<span>供给</span>${bar([[B.fuel_mass_flow_kg_per_s / tot, fuelVar, "燃料"], [B.oxidizer_mass_flow_kg_per_s / tot, "var(--lox)", "液氧"]])}` +
      `<span>排出</span>${bar([[B.main_mass_flow_kg_per_s / tot, "#C2412D", "主喷管"], [B.external_mass_flow_kg_per_s / tot, "#F2A65A", "外排"]])}</div>` +
      `<div class="bal-note">主喷管 <b>${fx(B.main_mass_flow_kg_per_s, 3)}</b>${gg ? ` + 外排 <b>${fx(B.external_mass_flow_kg_per_s, 3)}</b>` : `（含回流 <b>${fx(B.returned_mass_flow_kg_per_s, 3)}</b>）`} = <b>${fx(tot, 3)}</b> kg/s</div></div>` +
      `<div class="ledger"><h4>轴功账<span>残差 ${sci(B.shaft_residual_w)} W</span></h4><div class="bal">` +
      `<span>涡轮×η</span>${bar([[1, "#66758C", "涡轮×η轴"]])}<span>负载</span>${bar([[c.pump_w.fuel / shaftIn, fuelVar, "燃料泵"], [c.pump_w.oxidizer / shaftIn, "var(--lox)", "氧泵"], [c.inputs.auxiliary_power_w / shaftIn, "#B9C2D0", "辅助"]])}</div>` +
      `<div class="bal-note"><b>${W(shaftIn)}</b> = 燃料泵 <b>${W(c.pump_w.fuel)}</b> + 氧泵 <b>${W(c.pump_w.oxidizer)}</b> + 辅助 <b>${W(c.inputs.auxiliary_power_w)}</b></div></div>` +
      `<div class="ledger"><h4>焓账（Q = 0）<span>残差 ${fx(B.energy_residual_w, 3)} W</span></h4>` +
      `<div class="bal-note">入口焓流 <b>${W(B.inlet_enthalpy_rate_w)}</b> − 出口总焓流 <b>${W(B.exit_total_enthalpy_rate_w)}</b> = 辅助 + 机械损失 <b>${W(c.inputs.auxiliary_power_w + B.mechanical_loss_w)}</b></div></div>` +
      `<div class="ledger"><h4>元素账<span>最大 ${sci(Math.max(...c.element_residual.map(Math.abs)))}</span></h4>` +
      `<div class="bal-note">出口 C / H / O 相对残差 <b>${c.element_residual.map((x) => sci(x, 2)).join(" / ")}</b></div></div>`;
  }

  function buildForm() {
    const base = P.base, staged = P.env && P.env.ok ? P.env.result.case.staged : false;
    P.form.innerHTML = "";
    if (!base) return;
    CYCLE_FIELDS.forEach(([group, fields]) => {
      P.form.append(h("div", "g", group));
      fields.forEach(([key, label, unit, scale, only]) => {
        const off = (only === "gg" && staged) || (only === "sc" && !staged);
        const lab = h("label", "", `${label}${off ? `<small>${staged ? "补燃：由轴功反解" : "开式：不适用"}</small>` : ""}`);
        const box = h("div", "box", `<input type="number" step="any"${off ? " disabled" : ""}><span>${unit}</span>`);
        const wrap = h("div", key in P.over ? "changed" : ""); wrap.style.display = "contents"; wrap.append(lab, box);
        const input = box.querySelector("input");
        input.value = +((P.over[key] ?? base[key]) / scale).toPrecision(6);
        const commit = () => {
          const x = +input.value;
          if (input.value === "" || !Number.isFinite(x)) { box.classList.add("invalid"); return; }
          box.classList.remove("invalid");
          const si = x * scale;
          if (Math.abs(si - base[key]) <= 1e-9 * Math.max(1, Math.abs(base[key]))) delete P.over[key]; else P.over[key] = si;
          wrap.classList.toggle("changed", key in P.over);
          solve();
        };
        input.addEventListener("change", commit);
        input.addEventListener("keydown", (e) => { if (e.key === "Enter") input.blur(); });
        P.form.append(wrap);
      });
    });
    P.reset.disabled = !Object.keys(P.over).length;
  }

  function render() {
    const env = P.env;
    if (!env.ok) {
      P.k.forEach((k) => k.set({ refused: "C 拒算" }));
      fig.el.querySelector("h3").textContent = "循环求解拒算";
      fig.body.innerHTML = `<div style="position:absolute;inset:1rem">${failure(env, "输入组合不满足功率、压力或成分约束（例如涡轮出口压力不足以回流主室），C 核心不给近似解。点“恢复算例原值”回到文件输入。")}</div>`;
      ledgers.innerHTML = ""; detail.innerHTML = "";
      P.chain.set([{ name: "整机联立", val: env.status, state: "bad" }]);
      P.ev.set([["状态", env.status], ["C 消息", `<span style="font-family:var(--ff);white-space:normal">${esc(env.message)}</span>`]], CMD.cycle(P.file));
      return;
    }
    const c = cycleModel(env.result), B = c.balance, gg = !c.staged, name = CYCLE_CASES.find((x) => x[0] === P.file);
    fig.el.querySelector("h3").textContent = `${gg ? "燃气发生器开式循环" : "富氧补燃循环"}（${name[1]}背景）`;
    fig.body.innerHTML = cycleSchematic(c);
    const svgEl = fig.body.querySelector("svg");
    svgEl.querySelectorAll(".comp").forEach((gEl) => {
      const k = gEl.dataset.key;
      gEl.addEventListener("pointermove", (e) => { const [t, rows] = details(c, k); showTip(tipTable(t, rows), e.clientX, e.clientY); });
      gEl.addEventListener("pointerleave", hideTip);
      gEl.addEventListener("click", () => { P.pinned = k; svgEl.querySelectorAll(".comp").forEach((x) => x.classList.toggle("sel", x === gEl)); showDetail(c, k); });
    });
    if (!details(c, P.pinned) || !details(c, P.pinned)[1].length) P.pinned = "engine";
    svgEl.querySelectorAll(".comp").forEach((x) => x.classList.toggle("sel", x.dataset.key === P.pinned));
    showDetail(c, P.pinned);
    ledger(c);
    const minP = c.inputs.chamber_pressure_pa + c.inputs.return_pressure_drop_pa;
    P.k[0].set({ v: B.total_thrust_n / 1e3, d: 2, unit: "kN", foot: gg ? `主路 <b>${fx(B.main_thrust_n / 1e3, 2)}</b> + 外排 <b>${fx(B.branch_thrust_n / 1e3, 3)}</b>` : `主路 <b>${fx(B.main_thrust_n / 1e3, 2)}</b>，无外排` });
    P.k[1].set({ v: B.engine_specific_impulse_s, d: 2, unit: "s", foot: `总供给 <b>${fx(c.inputs.total_mass_flow_kg_per_s, 0)}</b> kg/s，${envName(c.inputs.ambient_pressure_pa)}` });
    P.k[2].set({ v: B.turbine_power_w / 1e6, d: 3, unit: "MW", foot: `泵 <b>${fx(B.pump_power_w / 1e6, 3)}</b> + 辅助 <b>${fx(c.inputs.auxiliary_power_w / 1e6, 2)}</b>，η轴 ${c.inputs.shaft_efficiency}` });
    P.k[3].set({ v: c.turbine.out_pa / 1e6, d: 2, unit: "MPa", foot: gg ? "给定外排背压" : `${badge("ok", "≥ 下限")}回流注入需 <b>${fx(minP / 1e6, 2)}</b> MPa` });
    P.chain.set([{ name: "泵", val: "2 × 恒密度" }, { name: gg ? "发生器 HP" : "预燃室 HP", val: `${fx(c.preburner.t, 0)} K` },
      { name: "涡轮冻结膨胀", val: gg ? "给定出口" : `出口压力二分 ${c.turbine_pressure_iterations} 次` },
      { name: gg ? "外排喷管" : "回流混合", val: gg ? `${fx(B.external_mass_flow_kg_per_s, 2)} kg/s` : `${fx(B.returned_mass_flow_kg_per_s, 1)} kg/s` },
      { name: "主室 HP", val: `${fx(c.chamber.t, 0)} K` }, { name: "主喷管", val: `喉 ${fx(B.main_throat_area_m2 * 1e4, 1)} cm²` },
      { name: "三本账闭合", val: `|ΔQ| ${fx(Math.abs(B.energy_residual_w), 2)} W` }]);
    P.key.innerHTML = `<h2>关键核对</h2><p>` + (gg
      ? `外排 <b>${fx(B.external_mass_flow_kg_per_s, 3)} kg/s</b> 经独立喷管仍贡献 <b>${fx(B.branch_thrust_n / 1e3, 3)} kN</b>，占整机 ${fx((B.branch_thrust_n / B.total_thrust_n) * 100, 2)}%，漏记即低估推力和比冲。发生器 O/F ${fx(c.inputs.preburner_oxidizer_fuel_ratio, 2)}，石墨活度 ${sci(c.preburner.ac, 3)}${c.preburner.ac < 1 ? " &lt; 1，仍在气相域内" : ""}。`
      : `轴功平衡反解涡轮出口 <b>${fx(c.turbine.out_pa / 1e6, 2)} MPa</b>，高于回流注入主室所需 <b>${fx(minP / 1e6, 2)} MPa</b>：功率账在注入约束内成立。${c.feed === "rp1_assigned" ? "RP-1 为指定替代物，燃料密度为假设值。" : ""}`) + "</p>";
    P.ev.set([["轴功残差", `${sci(B.shaft_residual_w)} W`], ["焓残差", `${fx(B.energy_residual_w, 3)} W`], ["质量相对残差", sci(B.mass_relative_residual)],
      ["元素最大残差", sci(Math.max(...c.element_residual.map(Math.abs)))]], CMD.cycle(P.file) + (Object.keys(P.over).length ? `   # 界面改了 ${Object.keys(P.over).length} 项输入` : ""));
  }
  function paintSweep() {
    P.swApi.redraw();
  }
  P.swApi = plotFrame(sw.body, (api) => {
    const e = P.sweep;
    if (!e) return plotMessage(api, "C 计算中…");
    if (!e.ok) return plotMessage(api, "扫描失败", "#B3261E");
    const r = e.result, def = CYCLE_SWEEPS.find((d) => d[0] === r.field), meta = CYCLE_FIELDS.flatMap((g) => g[1]).find((f) => f[0] === r.field);
    const scale = meta ? meta[3] : 1, xs = r.values.map((x) => x / scale), cur = (P.over[r.field] ?? P.base[r.field]) / scale;
    const pts = xs.map((x, i) => [x, r.isp[i]]).filter((p) => finite(p[1]));
    if (!pts.length) return plotMessage(api, "扫描范围内全部拒算", "#B3261E");
    const step = xs[1] - xs[0], bands = xs.map((x, i) => (r.message[i] ? { from: x - step / 2, to: x + step / 2 } : null)).filter(Boolean);
    const ys = pts.map((p) => p[1]), lo = Math.min(...xs), hi = Math.max(...xs);
    lineChart(api, { series: [{ pts, color: "#1F5FBF", name: "整机比冲", fmt: (v) => `${fx(v, 2)} s` }], bands,
      vlines: [{ x: cur, color: "#7A8496", dash: "4 4", label: "当前" }],
      x: { domain: [lo, hi], ticks: [lo, (lo + hi) / 2, hi].map((t) => +t.toPrecision(3)), title: `${def[1]}${meta && meta[2] ? ` / ${meta[2]}` : ""}`, name: def[1], fmtTip: (x) => fx(x, 3) },
      y: { domain: padDomain(Math.min(...ys), Math.max(...ys), 0.12), d: 1, title: "整机比冲 / s" },
      tip: (x) => { const i = xs.indexOf(x); return i >= 0 && finite(r.preburner_t[i]) ? `<b>预燃/发生器 ${fx(r.preburner_t[i], 0)} K · 推力 ${fx(r.thrust[i] / 1e3, 1)} kN</b><br>` : ""; } });
  });

  const run = RP.channel("cycle", (e) => {
    P.env = e;
    if (e.ok && !P.base) { P.base = e.result.inputs; buildForm(); }
    P.reset.disabled = !Object.keys(P.over).length;
    render();
  });
  const runSweep = RP.channel("cycle_sweep", (e) => { P.sweep = e; paintSweep(); });
  function sweep() {
    if (!P.base) return;
    const def = CYCLE_SWEEPS.find((d) => d[0] === P.sweepField), cur = P.over[def[0]] ?? P.base[def[0]];
    const hi = def[0] === "turbine_efficiency" ? Math.min(cur * def[3], 1) : cur * def[3];
    const lo = cur * def[2], n = 13;
    runSweep({ case: P.file, ...P.over, field: def[0], values: Array.from({ length: n }, (_, i) => +(lo + (hi - lo) * i / (n - 1)).toPrecision(6)) });
  }
  function solve() { run({ case: P.file, ...P.over }); sweep(); }
  function select(file) {
    P.file = file; P.over = {}; P.base = null; P.sweep = null;
    list.querySelectorAll("button").forEach((b) => b.setAttribute("aria-pressed", String(b.dataset.file === file)));
    RP.call("cycle", { case: file }).then((e) => {
      P.env = e; P.base = e.ok ? e.result.inputs : null; buildForm(); render(); sweep();
    });
  }
  select(P.file);
} });
