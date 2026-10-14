/* Tabs, keyboard shortcuts, motion toggle and provenance footer. */
(function main() {
  const nav = $("tabs"), buttons = [];
  TABS.forEach((t, i) => {
    t.init();
    const b = h("button", "", `<kbd>${i + 1}</kbd>${t.title}`);
    b.type = "button"; b.setAttribute("role", "tab"); b.setAttribute("aria-controls", `v-${t.id}`);
    b.addEventListener("click", () => select(i));
    b.addEventListener("keydown", (e) => {
      if (e.key === "ArrowRight" || e.key === "ArrowLeft") { e.preventDefault(); select((i + (e.key === "ArrowRight" ? 1 : TABS.length - 1)) % TABS.length, true); }
    });
    nav.append(b); buttons.push(b);
  });
  function select(i, focus) {
    TABS.forEach((t, j) => {
      const on = i === j;
      buttons[j].setAttribute("aria-selected", String(on)); buttons[j].tabIndex = on ? 0 : -1;
      $(`v-${t.id}`).hidden = !on;
    });
    hideTip();
    if (focus) buttons[i].focus();
    history.replaceState(null, "", `#${TABS[i].id}`);
  }
  const motion = $("motion");
  const setMotion = (on) => { motion.setAttribute("aria-pressed", String(on)); document.body.classList.toggle("still", !on); };
  motion.addEventListener("click", () => setMotion(motion.getAttribute("aria-pressed") !== "true"));
  if (REDUCED) setMotion(false);
  document.addEventListener("keydown", (e) => {
    if (e.target.tagName === "INPUT" || e.ctrlKey || e.metaKey || e.altKey) return;
    const n = "123456".indexOf(e.key);
    if (n >= 0 && n < TABS.length) select(n);
    if (e.key === "a" || e.key === "A") motion.click();
  });
  const pv = DATA.provenance;
  $("prov").innerHTML = `数据：rocketperf.exe（Release，已测）SHA-256 <code>${pv.binary_sha256.slice(0, 12)}</code> · ${fx(pv.c_runs, 0)} 次 C 运行 · ` +
    `生成 ${pv.generated_at.slice(0, 16).replace("T", " ")} UTC · 提交 <code>${pv.git_head}</code>`;
  const start = TABS.findIndex((t) => `#${t.id}` === location.hash);
  select(start >= 0 ? start : 0);
})();
