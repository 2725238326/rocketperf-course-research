/* Data access and formatting. Every number shown is read from DATA (C output or saved archive). */
const DATA = JSON.parse(document.getElementById("rp-data").textContent);
const AX = DATA.axes;
const ENV = [[0, "真空"], [5000, "5 kPa"], [50000, "50 kPa"], [101325, "海平面"]];
const TABS = [];
const $ = (id) => document.getElementById(id);
const ofKey = (of) => Number(of).toFixed(1);
const gridPt = (fuel, of, ar, pa) => DATA.grid[fuel][`${ofKey(of)}|${ar}|${pa}`];
const chamberPt = (of) => DATA.chamber[ofKey(of)];
const ok = (p) => !!p && p.status === "ok";
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));

const fx = (v, d) => Number(v).toLocaleString("zh-CN", { minimumFractionDigits: d, maximumFractionDigits: d });
const sgn = (v, d) => (v > 0 ? "+" : v < 0 ? "−" : "±") + fx(Math.abs(v), d);
const pct = (a, b) => (a / b - 1) * 100;
/* Scientific notation as HTML (sup) or SVG (tspan); plain decimals when readable. */
function sci(v, digits = 2, svg = false) {
  if (v === 0) return "0";
  const a = Math.abs(v);
  if (a >= 1e-3 && a < 1e5) return fx(v, a < 0.01 ? 4 : a < 1 ? 3 : digits);
  const e = Math.floor(Math.log10(a)), m = v / 10 ** e, ex = (e < 0 ? "−" : "") + Math.abs(e);
  return `${m.toFixed(digits - 1)}×10` + (svg ? `<tspan dy="-0.45em" font-size="0.72em">${ex}</tspan><tspan dy="0.45em"></tspan>` : `<sup>${ex}</sup>`);
}
const kpa = (pa) => (pa === 0 ? "0" : fx(pa / 1e3, pa < 1e4 ? 2 : 1));
const envName = (pa) => ENV.find((e) => e[0] === pa)[1];

/* C command for the current point, so any number on screen can be reproduced in a terminal. */
function command(kind, values) {
  return DATA.commands[kind].replace(/\{(\w+)\}/g, (_, k) => values[k]);
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

const tipEl = () => $("tip");
function showTip(html, x, y) {
  const t = tipEl();
  t.innerHTML = html; t.hidden = false;
  const r = t.getBoundingClientRect(), pad = 14;
  let left = x + pad, top = y + pad;
  if (left + r.width > innerWidth - 8) left = x - r.width - pad;
  if (top + r.height > innerHeight - 8) top = y - r.height - pad;
  t.style.left = `${Math.max(8, left)}px`; t.style.top = `${Math.max(8, top)}px`;
}
function hideTip() { tipEl().hidden = true; }
function tipTable(title, rows) {
  return `<div class="t">${title}</div><table>${rows.map(([k, v]) => `<tr><td>${k}</td><td>${v}</td></tr>`).join("")}</table>`;
}

function toast(text) {
  const t = $("toast");
  t.textContent = text; t.classList.add("show");
  clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove("show"), 1400);
}
function copyText(text) {
  const done = () => toast("已复制命令，可在仓库根目录直接运行");
  if (navigator.clipboard && window.isSecureContext) { navigator.clipboard.writeText(text).then(done, () => fallback()); return; }
  fallback();
  function fallback() {
    const a = document.createElement("textarea");
    a.value = text; a.style.position = "fixed"; a.style.opacity = "0"; document.body.appendChild(a); a.select();
    try { document.execCommand("copy"); done(); } catch (e) { toast("复制失败，请手动选择"); }
    a.remove();
  }
}

/* Peak of a [x, y] series, used for the optimum markers. */
function peakOf(pts) { return pts.reduce((a, p) => (p[1] > a[1] ? p : a), pts[0]); }
