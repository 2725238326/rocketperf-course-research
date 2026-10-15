"use strict";
/* Overview: calculation chain with live values, two vehicles' research cases, self-check. */
(() => {
  const VEHICLES = [
    { name: "朱雀三号 遥一", color: "var(--ch4)", prop: "液氧 / 甲烷",
      facts: "一级 9 台 TQ-12A 并联；二级 1 台 TQ-15A 真空型，可二次起动。", prefix: "zq3" },
    { name: "长征十号乙 首飞", color: "var(--rp1)", prop: "一级液氧 / 煤油 · 二级液氧 / 甲烷",
      facts: "一级 7 台液发 100 系列（130 吨级）；二级 140 吨级甲烷发动机，循环待判。", prefix: "cz10b" },
  ];
  let v, stages = {}, check;
  function stage(id, no, title, desc, view) {
    const n = el("div", { class: "stage" }, `<div class="no">${no}</div><h3>${title}</h3><p>${desc}</p><div class="val">—</div><div class="val2">&nbsp;</div>`);
    n.addEventListener("click", () => App.show(view));
    stages[id] = n;
    return n;
  }
  const set = (id, val, sub) => { stages[id].querySelector(".val").innerHTML = val; stages[id].querySelector(".val2").innerHTML = sub; };

  async function live() {
    const noz = await RP.call("nozzle", { fuel: "ch4", pc: 1e7, of: 2.6, ar: 40, pa: 0, at: 0.01 });
    if (noz.ok) {
      const r = noz.result;
      set("in", `${F.n(r.chamber.mixture_h / 1e3, 0)}<small>kJ/kg</small>`, `液甲烷 120 K · 液氧 100 K · 10 MPa 查表`);
      set("hp", `${F.n(r.chamber.gas.t, 0)}<small>K</small>`, `c* ${F.n(r.ideal.cstar, 1)} m/s · M̄ ${F.n(r.chamber.gas.mw, 2)}`);
      set("nz", `${F.n(r.attached.isp, 1)}<small>s</small>`, `真空 ε 40 · F ${F.n(r.attached.thrust / 1e3, 1)} kN`);
    }
    const first = App.info && App.info.cases.find((c) => c.ok);
    if (first) {
      const cy = await RP.call("cycle", { case: first.file });
      if (cy.ok) set("cy", `${F.n(cy.result.balance.isp, 1)}<small>s</small>`, `${first.label.split("·")[0]} · 支路 ${F.n(cy.result.balance.branch_flow, 2)} kg/s`);
    }
  }
  async function selfCheck(btn) {
    btn.disabled = true; check.textContent = "C 核心计算中…";
    const calls = [["chamber_sweep", { fuel: "ch4", of_min: 0.5, of_max: 4.5, n: 81 }, 81],
      ["nozzle_sweep", { fuel: "ch4", of: 2.6, ars: logspace(1.5, 150, 40), pas: [0, 5000, 50000, 101325] }, 160],
      ["compare", { ch4_of: 2.6, rp1_of: 2.6, ar: 10, pa: 0, n: 37 }, 38],
      ["chamber_sweep", { fuel: "rp1", of_min: 2.2, of_max: 4.0, n: 37 }, 37],
      ...(App.info ? App.info.cases.filter((c) => c.ok).map((c) => ["cycle", { case: c.file }, 1]) : [])];
    let ms = 0, points = 0, failed = 0;
    for (const [cmd, args, n] of calls) {
      const e = await RP.call(cmd, args);
      ms += e.elapsed_ms || 0; if (e.ok) points += n; else failed += 1;
    }
    check.innerHTML = failed ? `${failed} 次调用失败，详见各模块` :
      `✓ ${calls.length} 次 C 调用完成 ${points} 个工作点（平衡 + 喷管 + 循环），C 计算合计 ${F.n(ms, 1)} ms`;
    btn.disabled = false;
  }

  App.register("overview", {
    mount(info) {
      v = UI.view("overview", "", "");
      v.querySelector(".view-head").remove();
      const hero = el("section", { class: "hero" },
        `<h1>两型运载火箭动力系统 · 性能计算程序</h1>` +
        `<p>从推进剂入口状态出发，C17 核心依次求解燃烧室化学平衡、冻结喷管膨胀与涡轮泵循环平衡；每个数字都是程序当场计算，超出模型适用域时显式拒算并给出原因。</p>` +
        `<div class="row"><button class="btn primary" type="button" id="ov-check">运行性能自检</button><span class="selfcheck" id="ov-check-text">调用全部求解链，统计 C 计算耗时</span></div>` +
        `<svg class="flame" width="120" height="120" viewBox="0 0 24 24" fill="none" stroke="rgba(255,255,255,.55)" stroke-width="1" stroke-linejoin="round"><path d="M9 3h6v4l-1 3c2 4 4 7 5 11H5c1-4 3-7 5-11L9 7z"/><path d="M8 21c1 1.5 2.5 2 4 2s3-.5 4-2" stroke="rgba(255,160,90,.8)"/></svg>`);
      v.appendChild(hero);
      check = hero.querySelector("#ov-check-text");
      hero.querySelector("#ov-check").addEventListener("click", (e) => selfCheck(e.currentTarget));
      v.appendChild(el("div", { class: "guide", style: "margin:14px 0 0" },
        `<div><b>① 选模块</b><ul><li>左侧栏或数字键 1–6 切换；下方四个计算步骤卡片也可点击进入</li></ul></div>` +
        `<div><b>② 改输入</b><ul><li>每页左栏为输入：拖滑块，或在数字框输入后回车；单位标在框内，超范围标红</li></ul></div>` +
        `<div><b>③ 读输出</b><ul><li>右侧为 C 核心输出：顶部关键数值（悬停看定义）、状态条、曲线；“导出结果”保存 JSON，底栏命令可在控制台复现</li></ul></div>`));
      const pipe = el("div", { class: "pipeline", style: "margin-top:14px" });
      pipe.appendChild(stage("in", "01 · 入口", "推进剂入口状态", "液体物性查表 → 化学焓与元素库存", "chamber"));
      pipe.appendChild(stage("hp", "02 · 燃烧室", "HP 化学平衡", "九组分 CHO · 凝聚碳判据", "chamber"));
      pipe.appendChild(stage("nz", "03 · 喷管", "冻结流膨胀", "固定喉部 · 背压适用域评估", "nozzle"));
      pipe.appendChild(stage("cy", "04 · 循环", "涡轮泵功率平衡", "开式 / 富氧补燃 · 守恒闭合", "cycle"));
      v.appendChild(pipe);
      const grid = el("div", { class: "grid-2", style: "margin-top:14px" });
      VEHICLES.forEach((veh) => {
        const card = el("section", { class: "card vehicle" }, `<h3><span style="width:10px;height:10px;border-radius:3px;background:${veh.color};display:inline-block"></span>${veh.name}<span class="tag mute">${veh.prop}</span></h3><div class="facts">${veh.facts}</div>`);
        (info ? info.cases : []).filter((c) => c.object_ref && c.object_ref.startsWith(veh.prefix)).forEach((c) => {
          const row = el("div", { class: "case-row" }, `<span class="name">${c.label}</span><span class="tag ${c.evidence === "family_supported" ? "ok" : "warn"}">${c.evidence === "family_supported" ? "家族支持" : "待判情景"}</span><span class="go">打开循环 →</span>`);
          row.addEventListener("click", () => { App.show("cycle"); App.view("cycle").select(c.file); });
          card.appendChild(row);
        });
        card.appendChild(el("p", { class: "note", style: "margin-top:10px" }, "构型事实来自已核验公开资料；算例中的室压、流量、效率等为研究假设输入。"));
        grid.appendChild(card);
      });
      v.appendChild(grid);
      const tiles = el("div", { class: "grid-2", style: "margin-top:14px" });
      [["燃烧室", "改变室压、混合比、入口温度，实时看 T꜀、c*、产物组成和凝聚碳边界", "chamber"],
       ["喷管", "拖动面积比与背压，看附着、过膨胀与分离提示，以及匹配面积比", "nozzle"],
       ["推进剂", "同几何成对比较甲烷与 RP-1：比冲更高为何推力反而接近", "compare"],
       ["循环", "五个研究算例，编辑任一输入即重解功率、流量与守恒平衡", "cycle"]].forEach(([t, d, id], i) => {
        const c = el("div", { class: "case-row", style: "padding:12px 14px" }, `<span class="name"><b>${i + 2} · ${t}</b><br><span class="muted" style="font-size:12px">${d}</span></span><span class="go">进入 →</span>`);
        c.addEventListener("click", () => App.show(id)); tiles.appendChild(c);
      });
      v.appendChild(tiles);
      live();
    },
    cmd: () => "rocketperf.exe interactive",
  });
})();
