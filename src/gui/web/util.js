"use strict";
/* DOM helpers and number formatting. Formatting only rescales C outputs for display. */
const $ = (id) => document.getElementById(id);
const SVGNS = "http://www.w3.org/2000/svg";
function el(tag, attrs, html) {
  const node = document.createElement(tag);
  if (attrs) for (const [k, v] of Object.entries(attrs)) {
    if (k === "class") node.className = v; else if (k.startsWith("on")) node.addEventListener(k.slice(2), v); else node.setAttribute(k, v);
  }
  if (html !== undefined) node.innerHTML = html;
  return node;
}
function svg(tag, attrs, parent) {
  const node = document.createElementNS(SVGNS, tag);
  if (attrs) for (const [k, v] of Object.entries(attrs)) node.setAttribute(k, v);
  if (parent) parent.appendChild(node);
  return node;
}
const esc = (s) => String(s).replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
const finite = (v) => typeof v === "number" && Number.isFinite(v);
const clamp = (v, lo, hi) => Math.min(hi, Math.max(lo, v));
const css = (name) => getComputedStyle(document.documentElement).getPropertyValue(name).trim();

const F = {
  n(v, d = 2) {
    if (!finite(v)) return "—";
    return v.toLocaleString("zh-CN", { minimumFractionDigits: d, maximumFractionDigits: d });
  },
  /* Significant-figure style for quantities whose magnitude varies. */
  g(v, s = 4) {
    if (!finite(v)) return "—";
    if (v === 0) return "0";
    const a = Math.abs(v);
    if (a >= 1e-3 && a < 1e6) {
      const d = clamp(s - 1 - Math.floor(Math.log10(a)), 0, 6);
      return F.n(v, d);
    }
    return F.sci(v, s - 1);
  },
  sci(v, d = 2) {
    if (!finite(v)) return "—";
    if (v === 0) return "0";
    const e = Math.floor(Math.log10(Math.abs(v))), m = v / 10 ** e;
    return `${m.toFixed(d)}×10<sup>${e < 0 ? "−" : ""}${Math.abs(e)}</sup>`;
  },
  sciText(v, d = 2) { return F.sci(v, d).replace("<sup>", "^").replace("</sup>", ""); },
  sign(v, d = 2) { return !finite(v) ? "—" : (v > 0 ? "+" : v < 0 ? "−" : "±") + F.n(Math.abs(v), d); },
  pct(v, d = 2) { return !finite(v) ? "—" : F.sign(v, d) + "%"; },
  mpa: (pa) => F.g(pa / 1e6, 4),
  kpa: (pa) => (pa === 0 ? "0" : F.g(pa / 1e3, 4)),
  kn: (n) => F.n(n / 1e3, 1),
  mw: (w) => F.g(w / 1e6, 4),
  /* Ambient pressure label with the conventional names. */
  ambient(pa) {
    if (pa === 0) return "真空";
    if (Math.abs(pa - 101325) < 1) return "海平面";
    return `${F.kpa(pa)} kPa`;
  },
};
/* Species identifiers from C (H2O, CO2...) rendered with subscripts. */
const SPECIES_HTML = (id) => id.replace(/(\d+)/g, "<sub>$1</sub>");
const SPECIES_TEXT = (id) => id.replace(/\d/g, (d) => "₀₁₂₃₄₅₆₇₈₉"[d]);

function toast(text) {
  const t = $("toast");
  t.textContent = text; t.classList.add("show");
  clearTimeout(t._h); t._h = setTimeout(() => t.classList.remove("show"), 1600);
}
function copyText(text) {
  const area = el("textarea");
  area.value = text; area.style.position = "fixed"; area.style.opacity = "0";
  document.body.appendChild(area); area.select();
  let ok = false;
  try { ok = document.execCommand("copy"); } catch (e) { ok = false; }
  area.remove();
  toast(ok ? "已复制，可在发布目录运行 rocketperf.exe 复现" : "复制失败，请手动选择");
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
  return `<div class="t">${title}</div><table>${rows.map(([k, v, c]) =>
    `<tr><td>${c ? `<i style="background:${c}"></i>` : ""}${k}</td><td>${v}</td></tr>`).join("")}</table>`;
}
/* Linear interpolation of the zero crossing in a sampled series; null when none. */
function zeroCrossing(xs, ys) {
  for (let i = 1; i < xs.length; i++) {
    const a = ys[i - 1], b = ys[i];
    if (finite(a) && finite(b) && a !== b && (a <= 0) !== (b <= 0)) return xs[i - 1] + (xs[i] - xs[i - 1]) * (-a / (b - a));
  }
  return null;
}
function argmax(xs, ys) {
  let best = -1;
  ys.forEach((y, i) => { if (finite(y) && (best < 0 || y > ys[best])) best = i; });
  return best < 0 ? null : { x: xs[best], y: ys[best], i: best };
}
const linspace = (lo, hi, n) => Array.from({ length: n }, (_, i) => lo + (hi - lo) * i / (n - 1));
const logspace = (lo, hi, n) => linspace(Math.log10(lo), Math.log10(hi), n).map((e) => +(10 ** e).toPrecision(4));
