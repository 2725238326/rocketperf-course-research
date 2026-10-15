"use strict";
/* Bridge to the C core. In the desktop program window.rp is a WebView2 binding
 * that runs rp_gui_handle on a worker thread; in the browser preview the same
 * JSON goes to tools/gui_dev.py, which pipes it to the identical C bridge. */
const RP = (() => {
  const native = typeof window.rp === "function";
  let total = 0, lastMs = 0;
  async function raw(cmd, args) {
    const request = { cmd, args: args || {} };
    const t0 = performance.now();
    let env;
    try {
      if (native) {
        env = await window.rp(request);
        if (typeof env === "string") env = JSON.parse(env);
      } else {
        const r = await fetch("/rp", { method: "POST", body: JSON.stringify(request) });
        env = await r.json();
      }
    } catch (e) {
      env = { ok: false, cmd, status: "io_error", stage: "bridge", message: String(e && e.message || e) };
    }
    env.roundtrip_ms = performance.now() - t0;
    total += 1; lastMs = env.elapsed_ms || 0;
    status(env);
    return env;
  }
  function status(env) {
    const pill = $("calc-pill"), text = $("calc-text");
    pill.classList.toggle("fail", !env.ok && env.stage === "bridge");
    pill.classList.remove("busy");
    if (env.stage === "bridge" && !env.ok) { text.textContent = "C 核心不可用"; return; }
    text.textContent = `C 计算 ${env.elapsed_ms < 10 ? env.elapsed_ms.toFixed(2) : env.elapsed_ms.toFixed(0)} ms · 第 ${total} 次`;
  }
  /* Latest-wins channel: while a request is in flight only the newest pending
   * arguments are kept, so dragging a slider never queues stale solves. */
  function channel(cmd, onResult) {
    let inFlight = false, pending = null, seq = 0;
    async function pump() {
      if (inFlight || !pending) return;
      const args = pending; pending = null; inFlight = true;
      const mine = ++seq;
      $("calc-pill").classList.add("busy");
      const env = await raw(cmd, args);
      inFlight = false;
      /* Render every completed result (each is self-consistent) so dragging
       * shows intermediate states; the newest pending request runs next. */
      if (mine === seq) onResult(env, args);
      pump();
    }
    return (args) => { pending = args; pump(); };
  }
  return { native, call: raw, channel, get count() { return total; }, get lastMs() { return lastMs; } };
})();

const STATUS_ZH = {
  out_of_domain: "超出模型适用域", invalid_argument: "输入无效", not_bracketed: "求根区间无解",
  no_convergence: "迭代未收敛", numeric_error: "数值错误", io_error: "读写错误", parse_error: "请求格式错误",
};
const STAGE_ZH = { chamber: "燃烧室平衡", nozzle: "喷管", cstar: "特征速度", comparison: "推进剂对比", cycle: "循环求解", case: "算例读取", arguments: "参数", request: "请求", bridge: "界面桥接" };
/* Rejections keep the exact C status and message under a Chinese heading. */
function errorCard(env, hint) {
  const title = `${STAGE_ZH[env.stage] || env.stage || "计算"}：${STATUS_ZH[env.status] || env.status}`;
  return `<div class="card err-card"><div class="ic">!</div><div><h3>${esc(title)}</h3>` +
    `<p>${hint ? esc(hint) : "C 核心按显式失败契约拒绝此输入，未输出外推结果。"}</p>` +
    `<code>${esc(env.status)}: ${esc(env.message || "")}</code></div></div>`;
}
const CARBON_RE = /graphite activity ([\d.]+)/;
