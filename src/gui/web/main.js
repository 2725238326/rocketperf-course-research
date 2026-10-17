"use strict";
/* Tabs, keyboard shortcuts, motion and fullscreen toggles, provenance footer. */
window.addEventListener("DOMContentLoaded", async () => {
  const nav = $("tabs"), buttons = [];
  const info = await RP.call("info", {});
  $("prov").innerHTML = info.ok
    ? `rocketperf ${esc(info.result.version)} · ${esc(info.result.thermo_dataset)} · ${RP.native ? "C17 核心内置于本程序" : "浏览器预览经本地桥接调用同一 C 核心"}`
    : `<span style="color:var(--bad)">C 核心未响应：${esc(info.message || info.status)}</span>`;
  TABS.forEach((t, i) => {
    const b = h("button", "", `<kbd>${i + 1}</kbd>${t.title}`);
    b.type = "button"; b.setAttribute("role", "tab"); b.setAttribute("aria-controls", `v-${t.id}`);
    b.addEventListener("click", () => select(i));
    b.addEventListener("keydown", (e) => {
      if (e.key === "ArrowRight" || e.key === "ArrowLeft") { e.preventDefault(); select((i + (e.key === "ArrowRight" ? 1 : TABS.length - 1)) % TABS.length, true); }
    });
    nav.append(b); buttons.push(b);
  });
  /* Tabs initialise on first visit so start-up only waits for the first page's C calls. */
  const started = new Set();
  function select(i, focus) {
    const t = TABS[i];
    if (!started.has(t.id)) { started.add(t.id); t.init(); }
    TABS.forEach((x, j) => {
      const on = i === j;
      buttons[j].setAttribute("aria-selected", String(on)); buttons[j].tabIndex = on ? 0 : -1;
      const v = $(`v-${x.id}`); if (v) v.hidden = !on;
    });
    hideTip();
    if (focus) buttons[i].focus();
    history.replaceState(null, "", `#${t.id}`);
  }
  const motion = $("motion");
  const setMotion = (on) => { motion.setAttribute("aria-pressed", String(on)); document.body.classList.toggle("still", !on); };
  motion.addEventListener("click", () => setMotion(motion.getAttribute("aria-pressed") !== "true"));
  if (REDUCED) setMotion(false);
  async function fullscreen() {
    if (RP.native && typeof window.rp_fullscreen === "function") { await window.rp_fullscreen(); return; }
    if (document.fullscreenElement) document.exitFullscreen(); else document.documentElement.requestFullscreen().catch(() => {});
  }
  $("full").addEventListener("click", fullscreen);
  document.addEventListener("keydown", (e) => {
    if (e.target.tagName === "INPUT" || e.ctrlKey || e.metaKey || e.altKey) return;
    const n = "123456".indexOf(e.key);
    if (n >= 0 && n < TABS.length) select(n);
    if (e.key === "a" || e.key === "A") motion.click();
    if (e.key === "F11") { e.preventDefault(); fullscreen(); }
  });
  const start = TABS.findIndex((t) => `#${t.id}` === location.hash);
  select(start >= 0 ? start : 0);
  /* ?set=label:value,... types values into the visible page's controls; used to
   * script reproducible screenshots for the slides. */
  const preset = new URLSearchParams(location.search).get("set");
  if (preset) setTimeout(() => applyPreset(preset), 400);
});
function applyPreset(text) {
  const v = document.querySelector(".view:not([hidden])");
  for (const item of text.split(",")) {
    const [label, value] = item.split(":");
    const btn = [...v.querySelectorAll("button")].find((b) => b.textContent.trim().startsWith(label));
    if (btn && value === undefined) { btn.click(); continue; }
    const ctl = [...v.querySelectorAll(".ctl")].find((c) => c.querySelector("label") && c.querySelector("label").textContent.includes(label));
    const box = ctl && ctl.querySelector("input.num");
    if (box) { box.value = value; box.dispatchEvent(new Event("change")); }
  }
}
