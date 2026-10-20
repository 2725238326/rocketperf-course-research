"use strict";
/* Count physical results separately from domain diagnostics and rejected points. */
function selfCheckCounts(cmd, env) {
  if (!env.ok) return { solved: 0, diagnostic: 0, rejected: 0, failedCalls: 1 };
  const r = env.result;
  let solved = 0, diagnostic = 0, rejected = 0;
  if (cmd === "chamber_sweep") {
    solved = r.status.filter((s) => s === "ok").length;
    rejected = r.status.length - solved;
  } else if (cmd === "nozzle_sweep") {
    for (const row of r.regime) for (const value of row) {
      if (value === 0) solved += 1;
      else if (finite(value)) diagnostic += 1;
      else rejected += 1;
    }
  } else if (cmd === "compare") {
    solved = 1; // The selected pair is independent of the scan grid.
    for (let i = 0; i < r.sweep.of.length; i += 1) {
      if (finite(r.sweep.ch4_isp[i]) && finite(r.sweep.rp1_isp[i])) solved += 1;
      else rejected += 1;
    }
  } else if (cmd === "cycle") solved = 1;
  return { solved, diagnostic, rejected, failedCalls: 0 };
}

TABS.push({ id: "engineering", title: "计算自检", init() {
  const V = view("engineering"), data = ARCHIVE.validation;
  const archived = ["ch4", "rp1"].flatMap((f) => data[f].rows).filter((r) => r[3]);
  const archiveDate = ARCHIVE.provenance.generated_at.slice(0, 10);
  card(V.rail, "自检内容", "<p>运行燃烧室扫描、喷管网格、推进剂比较和五个循环算例，显示本次调用耗时及各循环的守恒残差。</p>" +
    "<p>扫描中的有效性能点、域诊断点和拒算点分别统计。调用成功不表示其中每个工作点都有性能解。</p>");
  card(V.rail, "结果含义", "<p>残差用于检查模型方程是否求解闭合。它不能代替真实发动机的性能误差、损失或寿命评估。</p>" +
    "<p>CEA 对照使用部分相同的物性数据，检查既定输入和物种范围内的软件结果。</p>");
  const self = card(V.rail, "运行检查", '<div class="presets"><button type="button">运行自检</button></div><div class="ev" style="margin-top:0.5rem"><table></table></div>');
  const selfTable = self.querySelector("table"), selfBtn = self.querySelector("button");
  const row = kpiRow(V.stage, 4);
  const live = kpi(row, "本次计算耗时", "全部自检调用合计");
  const valid = kpi(row, "性能求解成功", "一个推进剂成对结果计一项");
  const domain = kpi(row, "仅域诊断 / 拒算", "不计为有效性能点");
  const comparison = kpi(row, "保存的 CEA 对照", `归档日期 ${archiveDate}`);
  live.set({ html: '<div class="v muted">—</div>', foot: "尚未运行" });
  valid.set({ html: '<div class="v muted">—</div>', foot: "尚未运行" });
  domain.set({ html: '<div class="v muted">—</div>', foot: "尚未运行" });
  comparison.set({ v: archived.length, d: 0, unit: "字段", foot: `超过所设容差 <b>${archived.filter((r) => Math.abs(r[2]) > r[3]).length}</b> 项` });
  const g = figs(V.stage, "1.1fr 1fr");
  const residuals = figure(g, { title: "本次循环残差", sub: "显示当前 C 核心返回的质量、轴功与能量残差" }).body;
  residuals.innerHTML = '<p class="muted" style="padding:1rem">运行自检后显示五个循环算例的结果。</p>';
  figure(g, { title: "参考与适用范围", sub: "CEA 对照为保存结果，本页不重新运行 CEA" }).body.innerHTML =
    `<div class="scroll"><table class="data"><thead><tr><th>方法</th><th>保存的参考工况</th></tr></thead><tbody>` +
    `<tr><td>液态甲烷入口</td><td>${data.ch4.cea_cards} 组 CEA 对照</td></tr><tr><td>固定 RP-1 入口</td><td>${data.rp1.cea_cards} 组 CEA 对照</td></tr></tbody></table>` +
    `<p class="muted" style="padding:1rem">来源：${esc(data.ch4.archive)}、${esc(data.rp1.archive)}。条件与逐字段偏差见“CEA 对照”页。</p>` +
    `<p class="muted" style="padding:0 1rem">循环输入为研究假设；未包含实机泵图谱、完整冷却、瞬态和寿命模型。</p></div>`;
  takeaway(V.stage).textContent = "运行结果与保存的参考分开展示。计算耗时取决于本机环境；通过自检只说明本次调用和数值收支，不代表实机精度。";

  async function selfCheck() {
    selfBtn.disabled = true; selfBtn.textContent = "计算中…";
    const calls = [["燃烧室扫描", "chamber_sweep", { fuel: "ch4", pc: PC, of_min: 0.5, of_max: 4.5, n: 81 }],
      ["喷管网格", "nozzle_sweep", { fuel: "ch4", pc: PC, of: 2.6, at: AT, ars: [2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50, 60], pas: [0, 5000, 50000, 101325] }],
      ["推进剂比较", "compare", { ch4_of: 2.6, rp1_of: 2.6, ar: 10, pa: 0, at: AT, of_min: 2.2, of_max: 4.0, n: 37 }],
      ...CYCLE_CASES.map(([file, name, kind]) => [`${name} ${kind}`, "cycle", { case: file }])];
    let ms = 0;
    const total = { solved: 0, diagnostic: 0, rejected: 0, failedCalls: 0 }, rows = [], cyc = [];
    try {
      for (const [label, cmd, args] of calls) {
        const e = await RP.call(cmd, args), count = selfCheckCounts(cmd, e);
        ms += e.elapsed_ms || 0;
        for (const key of Object.keys(total)) total[key] += count[key];
        rows.push(`<tr><td style="text-align:left;font-family:var(--ff);white-space:normal;padding:.35rem 0">${esc(label)}<br><small class="muted">${e.ok ? `性能 ${count.solved} · 诊断 ${count.diagnostic} · 拒算 ${count.rejected}` : esc(e.status)}</small></td></tr>`);
        if (cmd === "cycle") {
          const b = e.ok ? e.result.balance : null;
          cyc.push(`<tr><td>${esc(label)}</td><td>${b ? sci(b.mass_relative, 2) : "—"}</td><td>${b ? sci(b.shaft_residual, 2) : "—"}</td><td>${b ? sci(b.energy_residual, 2) : "—"}</td></tr>`);
        }
      }
      selfTable.innerHTML = rows.join("");
      live.set({ v: ms, d: 0, unit: "ms", foot: `${calls.length} 次调用，失败 <b>${total.failedCalls}</b> 次` });
      valid.set({ v: total.solved, d: 0, unit: "项", foot: "按实际返回结果统计" });
      domain.set({ html: `<div class="v">${total.diagnostic} / ${total.rejected}</div>`, foot: "域诊断 / 拒算" });
      residuals.innerHTML = '<div class="scroll"><table class="data"><thead><tr><th>循环算例</th><th>质量相对残差</th><th>轴功 / W</th><th>能量 / W</th></tr></thead><tbody>' + cyc.join("") + "</tbody></table></div>";
    } finally {
      selfBtn.disabled = false; selfBtn.textContent = "再次运行";
    }
  }
  selfBtn.addEventListener("click", selfCheck);
} });
