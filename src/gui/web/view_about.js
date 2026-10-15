"use strict";
/* Model chain, datasets, boundaries and shortcuts. */
(() => {
  App.register("about", {
    mount(info) {
      const v = UI.view("about", "说明 · 模型与数据", "计算链、数据集、适用边界与操作方式");
      const g = el("div", { class: "grid-2 about" });
      const ds = info ? [["热力数据", info.thermo_dataset], ["液体入口查表", info.liquid_dataset], ["焓基准", info.liquid_basis],
        ["RP-1 指定反应物", info.kerosene_dataset], ["循环模型", info.cycle_model], ["程序版本", `rocketperf ${info.version}`]] : [];
      g.appendChild(UI.card("计算链", "", `<ul>
        <li><b>入口</b>：甲烷/氧单相液体双线性查表（CoolProp 7.1.0 HEOS 离线派生），给出密度、化学焓与元素库存；RP-1 用 CEA v3.3.4 指定反应物。</li>
        <li><b>燃烧室</b>：九组分 CHO 理想气体 HP 平衡（H₂ O₂ H₂O CO CO₂ CH₄ H O OH），1000–6000 K，石墨活度判凝聚碳。</li>
        <li><b>喷管</b>：燃烧室成分冻结、绝热无粘等熵膨胀，固定喉部面积由临界质量通量定流量。</li>
        <li><b>循环</b>：恒密度泵、冻结涡轮、单轴功率平衡；开式外排或富氧补燃回流，质量/能量/元素守恒闭合。</li></ul>`));
      g.appendChild(UI.card("数据集与版本", "", `<table class="data">${ds.map(([a, b]) => `<tr><td>${a}</td><td><code>${esc(b)}</code></td></tr>`).join("")}</table>`));
      g.appendChild(UI.card("适用边界", "程序在边界外拒算，不外推", `<ul>
        <li>凝聚碳（a꜀ &gt; 1）、温度超出 NASA9 区间、液体查表范围外的入口状态。</li>
        <li>喷管附着解仅 pₑ ≥ pₐ；过膨胀给理想公式参考与 0.4·pₐ 经验分离提示。</li>
        <li>RP-1 方法域：10 MPa、O/F 2.2–4.0、298.15 K / 90.170 K。</li>
        <li>循环无冷却、泵特性图、起动瞬态；外排喷管不模拟延伸段掺混。</li>
        <li>算例输入为研究假设，型号名称表示构型背景，不是实机标定参数。</li></ul>`));
      g.appendChild(UI.card("操作", "", `<ul>
        <li><span class="kbd">1</span>–<span class="kbd">6</span> 切换模块，<span class="kbd">T</span> 深浅色，<span class="kbd">F11</span> 全屏。</li>
        <li>滑块拖动即时重算；数字框输入后回车确认，超范围标红不提交。</li>
        <li>底栏为当前结果的等效命令，复制后在发布目录运行 <code>rocketperf.exe</code> 可得相同数值。</li>
        <li>所有计算由同一 C17 核心完成：${RP.native ? "本窗口通过 WebView2 绑定在工作线程调用 C 函数" : "浏览器预览经本地桥接进程调用同一 C 函数"}。</li></ul>`));
      v.appendChild(g);
    },
    cmd: () => "rocketperf.exe --help",
  });
})();
