"use strict";
/* Shared operating point, routing, header/footer and shortcuts. */
const FUEL = {
  ch4: { name: "液甲烷 / 液氧", short: "CH₄", color: "var(--ch4)", pc: [1, 20], of: [0.5, 4.5], ofStep: 0.01 },
  rp1: { name: "RP-1 / 液氧", short: "RP-1", color: "var(--rp1)", pc: [10, 10], of: [2.2, 4.0], ofStep: 0.01 },
};
/* Per-fuel memory so switching propellant restores that propellant's last inputs. */
const S = {
  fuel: "ch4",
  by: {
    ch4: { pc: 10, of: 2.6, tf: 120, to: 100, pf: 10, po: 10 },
    rp1: { pc: 10, of: 2.6, tf: 298.15, to: 90.17 },
  },
  ar: 40, pa: 0, at: 0.01,
  get p() { return this.by[this.fuel]; },
};
function pointArgs(extra) {
  const p = S.p, a = { fuel: S.fuel, pc: p.pc * 1e6, of: p.of };
  if (S.fuel === "ch4") Object.assign(a, { tf: p.tf, to: p.to, pf: p.pf * 1e6, po: p.po * 1e6 });
  return Object.assign(a, extra || {});
}
/* Plain decimals for the CLI parser (no exponent forms). */
const plain = (v) => (Number.isInteger(v) ? String(v) : String(+v.toPrecision(10)));
function cliPoint(kind, ar, pa, at) {
  const p = S.p;
  if (S.fuel === "rp1") return `rocketperf.exe combustion ${kind}-rp1 cea-v3.3.4-rp1-o2l-assigned-v1 liquid RP-1 O2(L) 10000000 ${plain(p.of)} 298.15 90.170` +
    (kind === "frozen" ? ` ${plain(ar)} ${plain(pa)} ${plain(at)}` : "");
  const mode = kind === "hp" ? "hp-liquid-state" : kind === "regime" ? "regime-liquid-state" : "frozen-liquid-state";
  return `rocketperf.exe combustion ${mode} coolprop710-cea334-liquid-molar-v1 heos710-cea334-ideal-zero-298.15-v1 liquid ` +
    `${plain(p.tf)} ${plain(p.pf * 1e6)} ${plain(p.to)} ${plain(p.po * 1e6)} ${plain(p.pc * 1e6)} ${plain(p.of)}` +
    (kind === "hp" ? "" : ` ${plain(ar)} ${plain(pa)} ${plain(at)}`) + (kind === "regime" ? " --text" : "");
}

const Bus = (() => {
  const subs = [];
  return { on: (fn) => subs.push(fn), emit: (what) => subs.forEach((fn) => fn(what)) };
})();

const App = (() => {
  const views = {};
  let current = null, info = null;
  function register(id, v) { views[id] = v; }
  function show(id) {
    if (!views[id]) return;
    current = id;
    document.querySelectorAll(".view").forEach((n) => n.classList.toggle("on", n.id === `view-${id}`));
    document.querySelectorAll("#rail button").forEach((b) => b.classList.toggle("on", b.dataset.view === id));
    if (views[id].show) views[id].show();
    footer();
  }
  function footer() {
    const v = views[current];
    $("foot-cmd").textContent = v && v.cmd ? v.cmd() : "—";
  }
  function pill() {
    const p = S.p;
    $("op-pill").innerHTML = `<b style="color:${FUEL[S.fuel].color}">${FUEL[S.fuel].short}</b> p<sub>c</sub> ${F.n(p.pc, 1)} MPa · O/F ${F.n(p.of, 2)}`;
  }
  async function fullscreen() {
    if (RP.native && typeof window.rp_fullscreen === "function") { await window.rp_fullscreen(); return; }
    if (document.fullscreenElement) document.exitFullscreen(); else document.documentElement.requestFullscreen().catch(() => {});
  }
  function theme(next) {
    const t = next || (document.documentElement.dataset.theme === "dark" ? "light" : "dark");
    document.documentElement.dataset.theme = t;
    try { localStorage.setItem("rp-theme", t); } catch (e) { /* storage may be unavailable */ }
    Bus.emit("theme");
  }
  async function boot() {
    try { theme(localStorage.getItem("rp-theme") || "light"); } catch (e) { theme("light"); }
    const env = await RP.call("info", {});
    info = env.ok ? env.result : null;
    $("foot-model").textContent = info ? `rocketperf ${info.version} · ${info.thermo_dataset}` : "C 核心未响应";
    Object.values(views).forEach((v) => v.mount && v.mount(info));
    document.querySelectorAll("#rail button").forEach((b) => b.addEventListener("click", () => show(b.dataset.view)));
    $("theme-btn").addEventListener("click", () => theme());
    $("full-btn").addEventListener("click", fullscreen);
    $("copy-cmd").addEventListener("click", () => copyText($("foot-cmd").textContent));
    const order = ["overview", "chamber", "nozzle", "compare", "cycle", "about"];
    document.addEventListener("keydown", (e) => {
      if ((e.target.closest && e.target.closest("input, select, textarea")) || e.ctrlKey || e.altKey || e.metaKey) return;
      if (e.key >= "1" && e.key <= "6") { show(order[+e.key - 1]); e.preventDefault(); }
      else if (e.key === "t" || e.key === "T") theme();
      else if (e.key === "F11") { fullscreen(); e.preventDefault(); }
    });
    Bus.on((what) => { if (what === "point") { pill(); footer(); } if (what === "cmd") footer(); });
    pill();
    show("overview");
  }
  return { register, show, boot, footer, view: (id) => views[id], get info() { return info; } };
})();
window.addEventListener("DOMContentLoaded", () => App.boot());
