"use strict";
/* Engine cycle: bundled vehicle research cases, editable inputs, schematic,
 * balance residuals and a one-field sweep. */
(() => {
  const GROUPS = [
    ["整机", [["total_mass_flow_kg_per_s", "总流量", "kg/s", 1], ["overall_oxidizer_fuel_ratio", "总体 O/F", "", 1],
             ["chamber_pressure_pa", "主室压力", "MPa", 1e6], ["main_area_ratio", "主喷管面积比", "", 1], ["ambient_pressure_pa", "环境压力", "kPa", 1e3]]],
    ["预燃室 / 发生器", [["preburner_pressure_pa", "压力", "MPa", 1e6], ["preburner_oxidizer_fuel_ratio", "O/F", "", 1],
             ["maximum_branch_fraction", "支路流量上限", "", 1]]],
    ["涡轮泵", [["turbine_efficiency", "涡轮效率", "", 1], ["turbine_outlet_pressure_pa", "涡轮出口压力", "MPa", 1e6, "gg"], ["shaft_efficiency", "轴效率", "", 1],
             ["fuel_pump_outlet_pressure_pa", "燃料泵出口", "MPa", 1e6], ["fuel_pump_efficiency", "燃料泵效率", "", 1],
             ["oxidizer_pump_outlet_pressure_pa", "氧泵出口", "MPa", 1e6], ["oxidizer_pump_efficiency", "氧泵效率", "", 1], ["auxiliary_power_w", "辅助功率", "kW", 1e3]]],
    ["管路", [["pump_to_chamber_drop_pa", "泵→主室压降", "MPa", 1e6], ["pump_to_preburner_drop_pa", "泵→预燃室压降", "MPa", 1e6],
             ["return_pressure_drop_pa", "回流压降", "MPa", 1e6, "sc"], ["branch_area_ratio", "外排喷管面积比", "", 1, "gg"]]],
  ];
  const SWEEP = { staged: [["preburner_oxidizer_fuel_ratio", "预燃室 O/F", 0.6, 1.4], ["chamber_pressure_pa", "主室压力", 0.7, 1.2], ["turbine_efficiency", "涡轮效率", 0.75, 1.25], ["main_area_ratio", "主喷管面积比", 0.5, 2]],
                  gg: [["preburner_oxidizer_fuel_ratio", "发生器 O/F", 0.8, 1.4], ["chamber_pressure_pa", "主室压力", 0.7, 1.2], ["turbine_efficiency", "涡轮效率", 0.75, 1.25], ["main_area_ratio", "主喷管面积比", 0.5, 2]] };
  const EVIDENCE = { family_supported: ["家族支持", "ok"], unresolved_scenario: ["待判情景", "warn"], method_only: ["方法算例", "mute"] };
  let v, caseFile = null, base = null, over = {}, env = null, sweepField = "preburner_oxidizer_fuel_ratio", k, banner, schem, resid, form, chart, setChart, picker, caseBox, inputsCard;
  const run = RP.channel("cycle", (e) => { env = e; if (e.ok && !base) base = e.result.inputs; paint(); });
  const runSweep = RP.channel("cycle_sweep", (e) => paintSweep(e));
  const update = () => { run({ case: caseFile, ...over }); sweep(); Bus.emit("cmd"); };

  function sweep() {
    if (!base) return;
    const staged = env && env.ok ? env.result.case.staged : false, def = SWEEP[staged ? "staged" : "gg"].find((d) => d[0] === sweepField);
    const cur = over[sweepField] ?? base[sweepField];
    let lo = cur * def[2], hi = cur * def[3];
    if (sweepField === "turbine_efficiency") hi = Math.min(hi, 1);
    runSweep({ case: caseFile, ...over, field: sweepField, values: linspace(lo, hi, 13).map((x) => +x.toPrecision(6)) });
  }
  function select(file) {
    caseFile = file; base = null; over = {}; env = null; form.innerHTML = "";
    caseBox.querySelectorAll(".case-row").forEach((r) => r.classList.toggle("on", r.dataset.file === file));
    caseBox.querySelectorAll(".case-row").forEach((r) => { r.style.borderColor = r.dataset.file === file ? "var(--accent)" : ""; });
    run({ case: caseFile });
    Bus.emit("cmd");
  }
  function buildForm(r) {
    const staged = r.case.staged;
    form.innerHTML = "";
    GROUPS.forEach(([title, fields]) => {
      form.appendChild(el("div", { class: "group-title", style: "margin-top:10px" }, title));
      const grid = el("div", { class: "field-grid" });
      fields.forEach(([key, label, unit, scale, only]) => {
        const disabled = (only === "gg" && staged) || (only === "sc" && !staged);
        const row = el("div", { "data-key": key });
        const val = (over[key] ?? r.inputs[key]) / scale;
        row.innerHTML = `<label>${label}${disabled ? `<small>${staged ? "补燃：自动求解/不适用" : "开式：不适用"}</small>` : ""}</label>` +
          `<div class="numbox wide"><input type="number" step="any" value="${+val.toPrecision(6)}" ${disabled ? "disabled" : ""}><span>${unit}</span></div>`;
        const input = row.querySelector("input"), box = row.querySelector(".numbox");
        const commit = () => {
          const x = +input.value;
          if (input.value === "" || !Number.isFinite(x)) { box.classList.add("invalid"); return; }
          box.classList.remove("invalid");
          const si = x * scale;
          if (Math.abs(si - base[key]) <= 1e-12 * Math.max(1, Math.abs(base[key]))) delete over[key]; else over[key] = si;
          row.classList.toggle("changed", key in over);
          update();
        };
        input.addEventListener("change", commit);
        input.addEventListener("keydown", (e) => { if (e.key === "Enter") input.blur(); });
        row.classList.toggle("changed", key in over);
        grid.appendChild(row);
      });
      form.appendChild(grid);
    });
    const f = r.fixed;
    form.appendChild(el("p", { class: "note", style: "margin-top:10px" }, `<b>来自算例文件（只读）</b> 燃料 ${F.n(f.fuel_temperature_k, 2)} K / ${F.n(f.fuel_density, 1)} kg/m³，氧 ${F.n(f.oxidizer_temperature_k, 2)} K / ${F.n(f.oxidizer_density, 1)} kg/m³，泵入口 ${F.mpa(f.fuel_pump_inlet_pressure_pa)} / ${F.mpa(f.oxidizer_pump_inlet_pressure_pa)} MPa。`));
    const reset = el("button", { class: "btn", type: "button", style: "margin-top:10px" }, "恢复算例原值");
    reset.addEventListener("click", () => { over = {}; buildForm(env.result); update(); });
    form.appendChild(reset);
    picker.innerHTML = "";
    picker.appendChild(UI.seg(SWEEP[staged ? "staged" : "gg"].map(([key, label]) => ({ value: key, label })), sweepField, (x) => { sweepField = x; sweep(); }, true).node);
  }

  function paint() {
    if (!env.ok) {
      ["isp", "f", "tc", "tpb", "pw", "br"].forEach((id) => k.set(id, "—", "", "拒算", true));
      UI.banner(banner, "bad", "×", `<b>循环求解拒算：${STATUS_ZH[env.status] || env.status}</b> 输入组合不满足功率/压力/成分约束，C 核心不给近似解。`, `${env.status}: ${env.message}`);
      schem.innerHTML = errorCard(env); resid.innerHTML = "";
      return;
    }
    const r = env.result, b = r.balance, staged = r.case.staged;
    if (!form.children.length) buildForm(r);
    k.set("isp", F.n(b.isp, 2), "s", "整机研究比冲");
    k.set("f", F.n(b.total_thrust / 1e3, 1), "kN", staged ? "主路" : `主路 ${F.n(b.main_thrust / 1e3, 1)} + 外排 ${F.n(b.branch_thrust / 1e3, 2)}`);
    k.set("tc", F.n(r.chamber.gas.t, 0), "K", `主室 O/F ${F.n(b.main_of, 2)}`);
    k.set("tpb", F.n(r.preburner.gas.t, 0), "K", `a꜀ ${F.sci(r.preburner.graphite_activity, 1)}`);
    k.set("pw", F.mw(b.pump_power), "MW", `涡轮 ${F.mw(b.turbine_power)} MW`);
    k.set("br", F.n(b.branch_flow / (b.fuel_flow + b.oxidizer_flow) * 100, 2), "%", `${F.n(b.branch_flow, 2)} kg/s`);
    const minP = r.inputs.chamber_pressure_pa + r.inputs.return_pressure_drop_pa;
    UI.banner(banner, "info", "i", staged
      ? `<b>富氧补燃：全部氧经预燃室驱动涡轮后回流主室，涡轮出口 ${F.mpa(r.turbine.out_p)} MPa ≥ 主室 + 回流压降 ${F.mpa(minP)} MPa。</b> 无外排损失，泵功率由 ${F.n(b.branch_flow, 1)} kg/s 富氧燃气提供。`
      : `<b>燃气发生器开式：${F.n(b.branch_flow / (b.fuel_flow + b.oxidizer_flow) * 100, 2)}% 推进剂驱动涡轮后外排。</b> 外排喷管推力 ${F.n(b.branch_thrust / 1e3, 2)} kN（占 ${F.n(b.branch_thrust / b.total_thrust * 100, 2)}%）计入整机，漏记会低估推力。`);
    Schem.cycle(schem, r);
    const d = r.diagnostics;
    resid.innerHTML = `<table class="data"><tr><th>守恒检查</th><th class="r">残差</th><th class="r">相对</th></tr>` +
      `<tr><td>质量</td><td class="r">${F.sci(b.mass_residual, 1)} kg/s</td><td class="r">${F.sci(b.mass_relative, 1)}</td></tr>` +
      `<tr><td>轴功</td><td class="r">${F.sci(b.shaft_residual, 1)} W</td><td class="r">${F.sci(b.shaft_relative, 1)}</td></tr>` +
      `<tr><td>能量 (Q=0)</td><td class="r">${F.sci(b.energy_residual, 1)} W</td><td class="r">${F.sci(b.energy_relative, 1)}</td></tr>` +
      `<tr><td>出口元素</td><td class="r">—</td><td class="r">${F.sci(d.exit_element_residual, 1)}</td></tr></table>` +
      UI.strip([["主喉面积", `${F.g(b.main_throat_area, 4)} m²`], ["主喷管 C<sub>F</sub>", F.n(r.main_nozzle.cf, 4)], ["主喷管 pₑ", `${F.kpa(r.main_nozzle.pe)} kPa`],
        ["涡轮比功", `${F.n(r.turbine.work / 1e3, 1)} kJ/kg`], ...(staged ? [["涡轮压力迭代", `${d.turbine_pressure_iterations} 次`]] : [])]).replace('class="strip"', 'class="strip" style="margin-top:10px"');
  }
  function paintSweep(e) {
    if (!e.ok) { chart.innerHTML = errorCard(e); return; }
    const r = e.result, def = Object.values(SWEEP).flat().find((d) => d[0] === r.field), meta = GROUPS.flatMap((g) => g[1]).find((f) => f[0] === r.field);
    const scale = meta ? meta[3] : 1, xs = r.values.map((x) => x / scale), cur = (over[r.field] ?? base[r.field]) / scale;
    setChart({
      x: { label: `${def ? def[1] : r.field}${meta && meta[2] ? ` / ${meta[2]}` : ""}`, tip: (x, i) => `${def ? def[1] : r.field} = ${F.g(x, 4)}` + (r.message[i] ? " · 拒算" : "") },
      y: { label: "整机比冲 / s" }, y2: { label: "预燃室温度 / K" },
      series: [{ name: "整机比冲", x: xs, y: r.isp, color: css("--accent"), format: (y) => `${F.n(y, 2)} s` },
               { name: "预燃/发生器温度", x: xs, y: r.preburner_t, axis: 2, color: css("--hot"), format: (y) => `${F.n(y, 0)} K` }],
      bands: xs.map((x, i) => (r.message[i] ? { from: x - (xs[1] - xs[0]) / 2, to: x + (xs[1] - xs[0]) / 2 } : null)).filter(Boolean),
      vlines: [{ x: cur, label: "当前", color: css("--ink-2"), bottom: true }],
    });
  }

  App.register("cycle", {
    mount(info) {
      v = UI.view("cycle", "发动机循环 · 功率与流量平衡", "单轴涡轮泵、绝热预燃室/发生器与主室联立：泵功 = 涡轮功，质量、能量与元素守恒闭合", {
        input: ["左侧选择研究算例（朱雀三号、长征十号乙各级）", "可编辑输入：总流量、O/F、主室压力、预燃室参数、泵与涡轮效率等；单位标在框内", "输入框改值后回车或点别处即重算，改过的项变蓝"],
        output: ["整机比冲、推力、主室与预燃室温度、泵功率、涡轮支路占比", "循环示意图标出各管路流量、温度、压力；线宽表示流量", "守恒检查表与单参数扫描曲线"],
        steps: ["先选算例看基准结果", "改一项输入观察循环如何重新平衡", "“恢复算例原值”回到文件中的输入"],
      }, () => env && env.ok && { inputs: { case: caseFile, overrides: { ...over } }, outputs: env });
      const panel = el("div", { class: "panel" });
      caseBox = el("div");
      (info ? info.cases : []).forEach((c) => {
        const ev = EVIDENCE[c.evidence] || ["—", "mute"];
        const row = el("div", { class: "case-row", "data-file": c.file }, `<span class="name">${c.label}</span>${c.ok ? `<span class="tag ${ev[1]}">${ev[0]}</span>` : `<span class="tag warn">缺文件</span>`}`);
        row.addEventListener("click", () => { if (c.ok) select(c.file); else toast(c.message); });
        caseBox.appendChild(row);
      });
      panel.appendChild(UI.card("研究算例", "型号仅作构型背景", caseBox));
      form = el("div");
      inputsCard = UI.card("可编辑输入", "修改后蓝色标注", form);
      panel.appendChild(inputsCard);
      const res = el("div", { class: "results" });
      k = UI.kpis([{ id: "isp", label: "整机比冲", sym: "I<sub>sp</sub>", color: "var(--accent)" }, { id: "f", label: "整机推力", sym: "F", color: "var(--hot)" },
        { id: "tc", label: "主室温度", sym: "T꜀", color: "var(--warn)" }, { id: "tpb", label: "预燃/发生器温度", sym: "T<sub>pb</sub>", color: "var(--hot)" },
        { id: "pw", label: "泵总功率", sym: "P<sub>pump</sub>", color: "#8b5cf6" }, { id: "br", label: "涡轮支路占比", sym: "ṁ<sub>b</sub>/ṁ", color: "var(--ch4)" }]);
      banner = el("div", { class: "banner info" });
      schem = el("div"); resid = el("div");
      chart = el("div", { class: "chart" }); setChart = Chart.mount(chart);
      picker = el("div");
      const top = el("div", { class: "grid-3", style: "grid-template-columns:1.75fr 1fr" });
      top.appendChild(UI.card("循环示意", "线宽 ∝ √流量", schem)); top.appendChild(UI.card("闭合检查", "C 求解器输出", resid));
      const sc = UI.card("单参数扫描", "每点独立求解；红色为拒算", chart); sc.querySelector(".card-h").appendChild(picker);
      [k.node, banner, top, sc].forEach((n) => res.appendChild(n));
      res.appendChild(el("p", { class: "note" }, "<b>模型</b> adiabatic_single_shaft_cycle_v1：恒密度泵、冻结涡轮与喷管、单轴、Q=0；无冷却、泵特性图与瞬态。算例数值为研究假设，型号名称只表示构型背景。"));
      const work = el("div", { class: "work" }); work.appendChild(panel); work.appendChild(res); v.appendChild(work);
      Bus.on((w) => { if (w === "theme" && env) paint(); });
      const first = info && info.cases.find((c) => c.ok);
      if (first) select(first.file);
    },
    show() { if (caseFile) Bus.emit("cmd"); },
    select: (file) => select(file),
    cmd: () => (caseFile ? `rocketperf.exe cycle adiabatic ${caseFile} --text${Object.keys(over).length ? "  (界面修改了 " + Object.keys(over).length + " 项输入)" : ""}` : "—"),
  });
})();
