"use strict";
/* Bridge to the C core, formatting and small helpers. In the desktop program
 * window.rp is a WebView2 binding that runs rp_gui_handle on a worker thread;
 * the browser preview posts the same JSON to tools/gui_dev.py, which pipes it
 * to the identical C bridge. Every number on screen comes from those replies. */
const $ = (id) => document.getElementById(id);
const TABS = [];
const ENV = [[0, "真空"], [5000, "5 kPa"], [50000, "50 kPa"], [101325, "海平面"]];
const PC = 1e7, AT = 0.01;
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
const finite = (v) => typeof v === "number" && Number.isFinite(v);
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const ofKey = (of) => Number(of).toFixed(1);
const range = (lo, hi, step) => Array.from({ length: Math.round((hi - lo) / step) + 1 }, (_, i) => +(lo + i * step).toFixed(6));

const fx = (v, d) => (finite(v) ? Number(v).toLocaleString("zh-CN", { minimumFractionDigits: d, maximumFractionDigits: d }) : "—");
const sgn = (v, d) => (v > 0 ? "+" : v < 0 ? "−" : "±") + fx(Math.abs(v), d);
const pct = (a, b) => (a / b - 1) * 100;
/* Scientific notation as HTML (sup) or SVG (tspan); plain decimals when readable. */
function sci(v, digits = 2, svg = false) {
  if (!finite(v)) return "—";
  if (v === 0) return "0";
  const a = Math.abs(v);
  if (a >= 1e-3 && a < 1e5) return fx(v, a < 0.01 ? 4 : a < 1 ? 3 : digits);
  const e = Math.floor(Math.log10(a)), m = v / 10 ** e, ex = (e < 0 ? "−" : "") + Math.abs(e);
  return `${m.toFixed(digits - 1)}×10` + (svg ? `<tspan dy="-0.45em" font-size="0.72em">${ex}</tspan><tspan dy="0.45em"></tspan>` : `<sup>${ex}</sup>`);
}
const kpa = (pa) => (pa === 0 ? "0" : fx(pa / 1e3, pa < 1e4 ? 2 : 1));
const envName = (pa) => (ENV.find((e) => e[0] === pa) || [pa, `${kpa(pa)} kPa`])[1];
const plain = (v) => (Number.isInteger(v) ? String(v) : String(+v.toPrecision(10)));
/* Equivalent CLI command for the current point, so any number can be reproduced in a terminal. */
const CMD = {
  ch4: (of, ar, pa, pc = PC) => `rocketperf.exe combustion frozen-liquid-state coolprop710-cea334-liquid-molar-v1 heos710-cea334-ideal-zero-298.15-v1 liquid 120 1e7 100 1e7 ${plain(pc)} ${plain(of)} ${plain(ar)} ${plain(pa)} 0.01`,
  rp1: (of, ar, pa) => `rocketperf.exe combustion frozen-rp1 cea-v3.3.4-rp1-o2l-assigned-v1 liquid RP-1 O2(L) 10000000 ${plain(of)} 298.15 90.170 ${plain(ar)} ${plain(pa)} 0.01`,
  regime: (of, ar, pa) => `rocketperf.exe combustion regime-liquid-state coolprop710-cea334-liquid-molar-v1 heos710-cea334-ideal-zero-298.15-v1 liquid 120 1e7 100 1e7 1e7 ${plain(of)} ${plain(ar)} ${plain(pa)} 0.01 --text`,
  cycle: (file) => `rocketperf.exe cycle adiabatic ${file} --text`,
};

const RP = (() => {
  const native = typeof window.rp === "function";
  let total = 0, inflight = 0;
  const pill = () => $("calc");
  function status(env) {
    const p = pill();
    p.classList.toggle("busy", inflight > 0);
    if (env.stage === "bridge" && !env.ok) { p.classList.add("fail"); p.querySelector("span").textContent = "C 核心不可用"; return; }
    p.classList.remove("fail");
    const ms = env.elapsed_ms || 0;
    p.querySelector("span").textContent = `C ${ms < 10 ? ms.toFixed(1) : ms.toFixed(0)} ms · ${total} 次`;
  }
  async function call(cmd, args) {
    const request = { cmd, args: args || {} };
    let env;
    inflight += 1; pill().classList.add("busy");
    try {
      if (native) { env = await window.rp(request); if (typeof env === "string") env = JSON.parse(env); }
      else { const r = await fetch("/rp", { method: "POST", body: JSON.stringify(request) }); env = await r.json(); }
    } catch (e) {
      env = { ok: false, cmd, status: "io_error", stage: "bridge", message: String((e && e.message) || e) };
    }
    inflight -= 1; total += 1; status(env);
    return env;
  }
  /* Latest-wins channel: while a request is in flight only the newest pending
   * arguments are kept, so dragging a slider never queues stale solves. */
  function channel(cmd, onResult) {
    let busy = false, pending = null;
    async function pump() {
      if (busy || !pending) return;
      const job = pending; pending = null; busy = true;
      const env = await call(cmd, job.args);
      busy = false;
      onResult(env, job.args, !pending, job.token);
      pump();
    }
    return (args, token) => { pending = { args, token }; pump(); };
  }
  /* Memoised call for sweeps whose arguments repeat (switching back and forth). */
  const memo = new Map();
  async function cached(cmd, args) {
    const key = cmd + JSON.stringify(args);
    if (!memo.has(key)) memo.set(key, call(cmd, args));
    const env = await memo.get(key);
    if (!env.ok && env.stage === "bridge") memo.delete(key);
    return env;
  }
  return { native, call, channel, cached, get count() { return total; } };
})();

const STATUS_ZH = { out_of_domain: "超出模型适用域", invalid_argument: "输入无效", not_bracketed: "求根区间无解",
  no_convergence: "迭代未收敛", numeric_error: "数值错误", io_error: "读写错误", parse_error: "请求格式错误" };
function failure(env, hint) {
  return `<div class="fail"><div><b>C 拒算：${esc(STATUS_ZH[env.status] || env.status)}</b>` +
    `<p>${hint || "C 核心按显式失败契约拒绝这组输入，不输出外推结果。"}</p><code>${esc(env.status)}: ${esc(env.message || "")}</code></div></div>`;
}

/* Smooth numeric change for KPI values; honours reduced motion. */
const REDUCED = matchMedia("(prefers-reduced-motion: reduce)").matches;
function tween(el, to, format) {
  const from = Number(el.dataset.v);
  el.dataset.v = to;
  if (REDUCED || !Number.isFinite(from) || from === to) { el.innerHTML = format(to); return; }
  const start = performance.now(), dur = 260, id = (el._tween = (el._tween || 0) + 1);
  const step = (t) => {
    if (el._tween !== id) return;
    const k = Math.min(1, (t - start) / dur), e = 1 - (1 - k) ** 3;
    el.innerHTML = format(from + (to - from) * e);
    if (k < 1) requestAnimationFrame(step);
  };
  requestAnimationFrame(step);
}

function showTip(html, x, y) {
  const t = $("tip");
  t.innerHTML = html; t.hidden = false;
  const r = t.getBoundingClientRect(), pad = 14;
  let left = x + pad, top = y + pad;
  if (left + r.width > innerWidth - 8) left = x - r.width - pad;
  if (top + r.height > innerHeight - 8) top = y - r.height - pad;
  t.style.left = `${Math.max(8, left)}px`; t.style.top = `${Math.max(8, top)}px`;
}
function hideTip() { $("tip").hidden = true; }
function tipTable(title, rows) {
  return `<div class="t">${title}</div><table>${rows.map(([k, v]) => `<tr><td>${k}</td><td>${v}</td></tr>`).join("")}</table>`;
}
function toast(text) {
  const t = $("toast");
  t.textContent = text; t.classList.add("show");
  clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove("show"), 1500);
}
function copyText(text, message = "已复制命令，可在发布目录用 rocketperf.exe 复现") {
  const a = document.createElement("textarea");
  a.value = text; a.style.position = "fixed"; a.style.opacity = "0"; document.body.appendChild(a); a.select();
  let ok = false;
  try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
  a.remove();
  toast(ok ? message : "复制失败，请手动选择");
}
function downloadText(filename, text) {
  const blob = new Blob([text], { type: "text/plain;charset=utf-8" });
  const url = URL.createObjectURL(blob), a = document.createElement("a");
  a.href = url; a.download = filename; a.style.display = "none";
  document.body.appendChild(a); a.click(); a.remove();
  setTimeout(() => URL.revokeObjectURL(url), 1000);
}
/* Peak of a [x, y] series, used for the optimum markers. */
function peakOf(pts) { return pts.reduce((a, p) => (p[1] > a[1] ? p : a), pts[0]); }
