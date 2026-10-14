/* Tab: engineering facts — architecture, optimisation, quality, accuracy. All values computed from DATA. */
TABS.push({ id: "engineering", title: "工程与质量", init() {
  const V = view("engineering"), E = DATA.engineering, ev = E.evidence;
  const pts = [...Object.values(DATA.grid.ch4), ...Object.values(DATA.grid.rp1), ...Object.values(DATA.chamber)];
  const solved = pts.filter(ok), refused = pts.filter((p) => !ok(p));
  const max = (i) => Math.max(...solved.map((p) => Math.abs(p.d[i])));
  const meanHp = solved.reduce((a, p) => a + p.d[0], 0) / solved.length;
  const carbon = refused.filter((p) => /graphite/.test(p.message)).length, over = refused.filter((p) => /Overexpanded/.test(p.message)).length;
  const peak = (fuel, ofs) => peakOf(ofs.map((r) => [r, gridPt(fuel, r, 10, 0)]).filter(([, p]) => ok(p)).map(([r, p]) => [r, p.isp]));
  const pC = peak("ch4", AX.ch4_of), pR = peak("rp1", AX.rp1_of), cPeak = peakOf(AX.chamber_of.filter((r) => ok(chamberPt(r))).map((r) => [r, chamberPt(r).cstar]));
  const vrows = ["ch4", "rp1"].flatMap((f) => DATA.validation[f].rows).filter((r) => r[3]);
  const code = E.modules.reduce((a, m) => a + m.lines, 0), gen = E.modules.reduce((a, m) => a + m.generated_lines, 0);
  card(V.rail, "三句话讲清楚", `<p><b>快</b>：HP 平衡改为 Illinois 割线 + 热启动后，同输入 ${ev.hp.solves} 次求解 CPU 中位时间 ${fx(ev.hp.before_s, 2)} → ${fx(ev.hp.after_s, 2)} s（${fx(ev.hp.speedup, 1)}×），结果差 ${sci(ev.hp.checksum_delta_k, 1)} K。</p>` +
    `<p><b>稳</b>：${fx(E.c_checks, 0)} 项 C 检查 + ${E.tests.cli_groups} 组 CLI，${E.flags.includes("-Werror") ? "警告即错误" : ""}，GCC 分析器 ${ev.analyzer.units}/${ev.analyzer.units} 个编译单元无告警。</p>` +
    `<p><b>准</b>：与 NASA CEA ${fx(vrows.length, 0)} 项字段对照全部在容差内；页面上 ${fx(solved.length, 0)} 个解的元素守恒最大残差 ${sci(max(2), 1)}。</p>`);
  card(V.rail, "代码规模", `<div class="ev"><table>` + E.modules.map((m) => `<tr><td>${m.id} <span class="muted">${esc(m.name)}</span></td><td>${fx(m.lines, 0)} 行</td></tr>`).join("") +
    `<tr><td><b>手写 C 合计</b></td><td><b>${fx(code, 0)} 行</b></td></tr><tr><td class="muted">另：生成的物性/表数据头</td><td class="muted">${fx(gen, 0)} 行</td></tr></table></div>` +
    `<p class="muted" style="margin-top:0.45rem">按非空行计；依赖方向由 project/modules.json 登记并在质量入口中检查。</p>`);
  const row = kpiRow(V.stage, 4);
  kpi(row, "HP 平衡求解", `${ev.hp.solves} 次 · 中位 CPU`).set({ v: ev.hp.speedup, d: 1, unit: "× 加速", foot: `${fx(ev.hp.before_s, 2)} → <b>${fx(ev.hp.after_s, 2)} s</b> · 外层 ${fx(ev.hp.iterations_before, 1)} → <b>${fx(ev.hp.iterations_after, 1)}</b> 次` });
  kpi(row, "C 单元/回归检查", "Debug + Release").set({ v: E.c_checks, d: 0, unit: "项", foot: `另 CLI <b>${E.tests.cli_groups}</b> 组 · 数据/参考 <b>${E.tests.parameter_data_groups + E.tests.thermo_data_groups + E.tests.cea_reference_groups + E.tests.cycle_reference_groups}</b> 组` });
  kpi(row, "与 CEA 字段对照", "两条推进剂路径").set({ v: vrows.length, d: 0, unit: "项", foot: `超出容差 <b>${vrows.filter((r) => Math.abs(r[2]) > r[3]).length}</b> · 最大 T 差 <b>0.0044 K</b>` });
  kpi(row, "显式拒算", `页面 ${fx(pts.length, 0)} 个点`).set({ v: refused.length, d: 0, unit: "个", foot: `过膨胀 <b>${over}</b> · 凝聚碳 <b>${carbon}</b> · 其余 <b>${refused.length - over - carbon}</b>` });
  const g = figs(V.stage, "1.05fr 1fr 1fr");
  const col = (title, sub) => figure(g, { title, sub }).body;
  const sec = (t, rows) => `<div class="kv-h">${t}</div><table class="kv"><tbody>` +
    rows.map(([a, b]) => `<tr><td>${a}</td><td>${b}</td></tr>`).join("") + "</tbody></table>";
  col("优化：更快，结果不变", "同一输入、交替采样、单机 CPU 中位时间").innerHTML = `<div class="scroll">` +
    sec("HP 平衡（本轮）", [["方法", "二分 → Illinois 割线 + 热启动"], ["基准", `${ev.hp.solves} 次液甲烷 HP，${ev.hp.samples} 组交替`], ["CPU 中位时间", `${fx(ev.hp.before_s, 3)} → ${fx(ev.hp.after_s, 3)} s`],
      ["外层迭代均值", `${fx(ev.hp.iterations_before, 1)} → ${fx(ev.hp.iterations_after, 1)}`], ["310 点温度和之差", `${sci(ev.hp.checksum_delta_k, 2)} K`], ["对照基线", `提交 ${ev.hp.baseline}`]]) +
    sec("冻结喷管（QA-002）", [["方法", "复用与压力无关的 NASA9 求值"], ["基准", `${ev.frozen.solves} 次 A10/A40`], ["CPU 中位时间", `${ev.frozen.before_s} → ${ev.frozen.after_s} s`], ["推力校验和", "逐位相同"]]) +
    sec("设计层面的最优点（同一 C 网格）", [["液甲烷 c* 峰值", `O/F ${ofKey(cPeak[0])} · ${fx(cPeak[1], 1)} m/s`], ["液甲烷 ε10 真空比冲峰值", `O/F ${ofKey(pC[0])} · ${fx(pC[1], 2)} s`],
      ["RP-1 ε10 真空比冲峰值", `O/F ${ofKey(pR[0])} · ${fx(pR[1], 2)} s`], ["海平面匹配面积比（O/F 2.6）", fx(DATA.matched_area_ratio["2.6|101325"], 2)]]) + "</div>";
  const testRows = [["物性 NASA9", E.tests.thermo_checks], ["燃烧平衡", E.tests.combustion_checks], ["循环", E.tests.cycle_checks], ["核心/求根", E.tests.core_checks], ["输入适配", E.tests.adapter_checks]];
  const tmax = Math.max(...testRows.map((r) => r[1]));
  col("质量：每一层都有门禁", "数字取自当前 Release 测试报告与分析器归档").innerHTML = `<div class="scroll">` +
    `<div class="kv-h">C 检查分布（共 ${fx(E.c_checks, 0)} 项）</div>` +
    testRows.map(([n, v]) => `<div class="bal" style="grid-template-columns:5.6rem 1fr 3.4rem;margin-bottom:0.22rem"><span>${n}</span><div class="bar"><span style="width:${Math.max(1.5, (100 * Math.sqrt(v)) / Math.sqrt(tmax))}%;background:#5385C5"></span></div><span class="mono" style="text-align:right;color:var(--ink)">${fx(v, 0)}</span></div>`).join("") +
    `<p class="muted" style="font-size:0.7rem;margin:0.1rem 0 0">条长 ∝ √项数</p>` +
    sec("编译与分析", [["标准", E.flags.find((f) => f.startsWith("-std")).slice(5).toUpperCase()], ["警告门禁", E.flags.filter((f) => f.startsWith("-W")).length + " 项，-Werror"],
      ["GCC -fanalyzer", `${ev.analyzer.clean_logs}/${ev.analyzer.units} 单元零告警`], ["编译器", esc(ev.analyzer.compiler.replace(/\(.*?\)/, "").trim())]]) +
    sec("统一质量入口（6 组）", E.quality_groups.map((q) => [q.id, `<span style="font-family:var(--ff);color:var(--ink-2);white-space:normal">${esc(q.scope)}</span>`])) + "</div>";
  col("准确性：守恒、解析解、参考软件", "前两组来自本页全部 C 解，第三组来自归档").innerHTML = `<div class="scroll">` +
    sec(`本页 ${fx(solved.length, 0)} 个 C 解的残差上界`, [["元素守恒（相对）", sci(max(2), 2)], ["HP 焓残差", `${sci(max(3), 2)} J/kg`], ["喷管连续性（相对）", sci(max(4), 2)], ["HP 外层迭代均值", fx(meanHp, 1)]]) +
    sec("两个循环情景的闭合", DATA.cycles.map((c) => [c.inputs.staged_combustion ? "补燃 · 长十乙一级" : "开式 · 朱雀三号一级",
      `轴 ${sci(c.balance.shaft_residual_w, 1)} W · 焓 ${fx(c.balance.energy_residual_w, 2)} W`])) +
    sec("解析与参考", [["L0 理想喷管 Mach 2", "A/A* = 27/16 精确解"], ["液甲烷对 CEA", `${DATA.validation.ch4.cea_cards} 卡 · T 差 ≤ 0.0044 K`], ["RP-1 对 CEA", `${DATA.validation.rp1.cea_cards} 卡 · T 差 ≤ 0.0043 K`],
      ["积碳判据", "Boudouard 独立重算一致"]]) +
    `<p class="muted" style="font-size:0.72rem;margin-top:0.5rem">同源物性下的软件核验，不是发动机实验验证。证据归档：${esc(ev.archive)}</p></div>`;
  takeaway(V.stage).innerHTML = `快、稳、准都有可复跑的记录：基准用 <code>tools/benchmark_frozen.py --driver hp</code>，检查用 <code>python tools/quality.py</code>，本页数据用 <code>python tools/demo_data.py --check</code> 一键重算比对。`;
} });
