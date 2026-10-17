"use strict";
/* Tab: engineering facts. Architecture, speed-up and test counts come from the
 * archived evidence (ARCHIVE); the self-check runs the live C core and reports
 * its own residuals and timings. */
TABS.push({ id: "engineering", title: "工程与质量", init() {
  const V = view("engineering"), E = ARCHIVE.engineering, ev = E.evidence;
  const vrows = ["ch4", "rp1"].flatMap((f) => ARCHIVE.validation[f].rows).filter((r) => r[3]);
  const code = E.modules.reduce((a, m) => a + m.lines, 0), gen = E.modules.reduce((a, m) => a + m.generated_lines, 0);
  card(V.rail, "三句话讲清楚", `<p><b>快</b>：HP 平衡改为 Illinois 割线 + 热启动后，同输入 ${ev.hp.solves} 次求解 CPU 中位时间 ${fx(ev.hp.before_s, 2)} → ${fx(ev.hp.after_s, 2)} s（${fx(ev.hp.speedup, 1)}×），结果差 ${sci(ev.hp.checksum_delta_k, 1)} K。</p>` +
    `<p><b>稳</b>：${fx(E.c_checks, 0)} 项 C 检查 + ${E.tests.cli_groups} 组 CLI，${E.flags.includes("-Werror") ? "警告即错误" : ""}，GCC 分析器 ${ev.analyzer.clean_logs}/${ev.analyzer.units} 个编译单元无告警。</p>` +
    `<p><b>准</b>：与 NASA CEA ${fx(vrows.length, 0)} 项字段对照全部在容差内；下方自检当场调用 C 并报告守恒残差。</p>`);
  card(V.rail, "代码规模", `<div class="ev"><table>` + E.modules.map((m) => `<tr><td>${m.id} <span class="muted">${esc(m.name)}</span></td><td>${fx(m.lines, 0)} 行</td></tr>`).join("") +
    `<tr><td><b>C 核心合计</b></td><td><b>${fx(code, 0)} 行</b></td></tr><tr><td class="muted">另：生成的物性/表数据头</td><td class="muted">${fx(gen, 0)} 行</td></tr></table></div>` +
    `<p class="muted" style="margin-top:0.45rem">按非空行计；不含界面桥接 src/gui。依赖方向由 project/modules.json 登记并在质量入口中检查。</p>`);
  const self = card(V.rail, "现场自检", `<p>调用全部求解链：燃烧室扫描、喷管网格、推进剂对比与 5 个循环算例，统计 C 计算耗时和守恒残差。</p><div class="presets"><button type="button">运行自检</button></div><div class="ev" style="margin-top:0.5rem"><table></table></div>`);
  const selfTable = self.querySelector("table"), selfBtn = self.querySelector("button");
  const row = kpiRow(V.stage, 4);
  kpi(row, "HP 平衡求解", `${ev.hp.solves} 次 · 中位 CPU`).set({ v: ev.hp.speedup, d: 1, unit: "× 加速", foot: `${fx(ev.hp.before_s, 2)} → <b>${fx(ev.hp.after_s, 2)} s</b> · 外层 ${fx(ev.hp.iterations_before, 1)} → <b>${fx(ev.hp.iterations_after, 1)}</b> 次` });
  kpi(row, "C 单元/回归检查", "Debug + Release").set({ v: E.c_checks, d: 0, unit: "项", foot: `另 CLI <b>${E.tests.cli_groups}</b> 组 · 数据/参考 <b>${E.tests.parameter_data_groups + E.tests.thermo_data_groups + E.tests.cea_reference_groups + E.tests.cycle_reference_groups}</b> 组` });
  kpi(row, "与 CEA 字段对照", "两条推进剂路径").set({ v: vrows.length, d: 0, unit: "项", foot: `超出容差 <b>${vrows.filter((r) => Math.abs(r[2]) > r[3]).length}</b> 项` });
  const live = kpi(row, "本机 C 自检", "点左侧运行");
  live.set({ html: '<div class="v muted">—</div>', foot: "未运行" });
  const g = figs(V.stage, "1.05fr 1fr 1fr");
  const col = (title, sub) => figure(g, { title, sub }).body;
  const sec = (t, rows) => `<div class="kv-h">${t}</div><table class="kv"><tbody>` + rows.map(([a, b]) => `<tr><td>${a}</td><td>${b}</td></tr>`).join("") + "</tbody></table>";
  col("优化：更快，结果不变", "同一输入、交替采样、单机 CPU 中位时间").innerHTML = `<div class="scroll">` +
    sec("HP 平衡", [["方法", "二分 → Illinois 割线 + 热启动"], ["基准", `${ev.hp.solves} 次液甲烷 HP，${ev.hp.samples} 组交替`], ["CPU 中位时间", `${fx(ev.hp.before_s, 3)} → ${fx(ev.hp.after_s, 3)} s`],
      ["外层迭代均值", `${fx(ev.hp.iterations_before, 1)} → ${fx(ev.hp.iterations_after, 1)}`], ["310 点温度和之差", `${sci(ev.hp.checksum_delta_k, 2)} K`], ["对照基线", `提交 ${ev.hp.baseline}`]]) +
    sec("冻结喷管", [["方法", "复用与压力无关的 NASA9 求值"], ["基准", `${ev.frozen.solves} 次 A10/A40`], ["CPU 中位时间", `${ev.frozen.before_s} → ${ev.frozen.after_s} s`], ["推力校验和", "逐位相同"]]) +
    sec("界面调用", [["线程", RP.native ? "WebView2 绑定 → 工作线程调用 C" : "浏览器预览 → 本地桥接进程调用同一 C"], ["拖动策略", "只保留最新请求，不排队旧解"], ["结果来源", "与 rocketperf.exe 同一求解函数"]]) + "</div>";
  const testRows = [["物性 NASA9", E.tests.thermo_checks], ["燃烧平衡", E.tests.combustion_checks], ["循环", E.tests.cycle_checks], ["核心/求根", E.tests.core_checks], ["输入适配", E.tests.adapter_checks]];
  const tmax = Math.max(...testRows.map((r) => r[1]));
  col("质量：每一层都有门禁", "数字取自 Release 测试报告与分析器归档").innerHTML = `<div class="scroll">` +
    `<div class="kv-h">C 检查分布（共 ${fx(E.c_checks, 0)} 项）</div>` +
    testRows.map(([n, v]) => `<div class="bal" style="grid-template-columns:5.6rem 1fr 3.4rem;margin-bottom:0.22rem"><span>${n}</span><div class="bar"><span style="width:${Math.max(1.5, (100 * Math.sqrt(v)) / Math.sqrt(tmax))}%;background:#5385C5"></span></div><span class="mono" style="text-align:right;color:var(--ink)">${fx(v, 0)}</span></div>`).join("") +
    `<p class="muted" style="font-size:0.7rem;margin:0.1rem 0 0">条长 ∝ √项数</p>` +
    sec("编译与分析", [["标准", E.flags.find((f) => f.startsWith("-std")).slice(5).toUpperCase()], ["警告门禁", `${E.flags.filter((f) => f.startsWith("-W")).length} 项，-Werror`],
      ["GCC -fanalyzer", `${ev.analyzer.clean_logs}/${ev.analyzer.units} 单元零告警`], ["编译器", esc(ev.analyzer.compiler.replace(/\(.*?\)/, "").trim())]]) +
    sec("统一质量入口（6 组）", E.quality_groups.map((q) => [q.id, `<span style="font-family:var(--ff);color:var(--ink-2);white-space:normal">${esc(q.scope)}</span>`])) + "</div>";
  const acc = col("准确性：守恒、解析解、参考软件", "第一组为本机自检，其余来自归档");
  const accFixed = sec("解析与参考", [["L0 理想喷管 Mach 2", "A/A* = 27/16 精确解"], ["液甲烷对 CEA", `${ARCHIVE.validation.ch4.cea_cards} 卡`], ["RP-1 对 CEA", `${ARCHIVE.validation.rp1.cea_cards} 卡`], ["积碳判据", "Boudouard 独立重算一致"]]);
  acc.innerHTML = `<div class="scroll"><div class="kv-h">本机自检</div><p class="muted" style="font-size:0.84rem">运行自检后显示各循环算例的轴功与焓残差。</p>${accFixed}</div>`;
  takeaway(V.stage).innerHTML = `快、稳、准都有可复跑的记录：基准用 <code>tools/benchmark_frozen.py --driver hp</code>，检查用 <code>python tools/quality.py</code>；界面数值与 <code>rocketperf.exe</code> 的一致性由 <code>tests/test_gui.py</code> 逐项比对。`;

  async function selfCheck() {
    selfBtn.disabled = true; selfBtn.textContent = "C 计算中…";
    const calls = [["燃烧室扫描 81 点", "chamber_sweep", { fuel: "ch4", pc: PC, of_min: 0.5, of_max: 4.5, n: 81 }, 81],
      ["喷管网格 60 点", "nozzle_sweep", { fuel: "ch4", pc: PC, of: 2.6, at: AT, ars: [2, 3, 4, 5, 6, 8, 10, 12, 15, 20, 25, 30, 40, 50, 60], pas: [0, 5000, 50000, 101325] }, 60],
      ["推进剂成对 37 点", "compare", { ch4_of: 2.6, rp1_of: 2.6, ar: 10, pa: 0, at: AT, of_min: 2.2, of_max: 4.0, n: 37 }, 38],
      ...CYCLE_CASES.map(([file, name, kind]) => [`${name} ${kind}`, "cycle", { case: file }, 1])];
    let ms = 0, points = 0, failed = 0;
    const rows = [], cyc = [];
    for (const [label, cmd, args, n] of calls) {
      const e = await RP.call(cmd, args);
      ms += e.elapsed_ms || 0;
      if (e.ok) points += n; else failed += 1;
      rows.push([label, e.ok ? `${fx(e.elapsed_ms, e.elapsed_ms < 10 ? 1 : 0)} ms` : `<span style="color:var(--bad)">${esc(e.status)}</span>`]);
      if (cmd === "cycle" && e.ok) cyc.push([label, `轴 ${sci(e.result.balance.shaft_residual, 1)} W · 焓 ${fx(e.result.balance.energy_residual, 2)} W`]);
    }
    selfTable.innerHTML = rows.map(([a, b]) => `<tr><td>${a}</td><td>${b}</td></tr>`).join("");
    live.set({ v: ms, d: 0, unit: "ms", foot: failed ? `<b>${failed}</b> 次调用失败` : `${calls.length} 次调用 · <b>${points}</b> 个工作点全部求解` });
    acc.innerHTML = `<div class="scroll">${sec("本机自检：循环闭合", cyc)}${accFixed}</div>`;
    selfBtn.disabled = false; selfBtn.textContent = "再次运行";
  }
  selfBtn.addEventListener("click", selfCheck);
} });
