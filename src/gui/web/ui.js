"use strict";
/* Reusable controls. Values are held in display units (MPa, kPa) and converted
 * by the views; validation here is input hygiene, physics domains stay in C. */
const UI = (() => {
  function slider(o) {
    const log = !!o.log, steps = 1000;
    const toPos = (v) => (log ? (Math.log(v / o.min) / Math.log(o.max / o.min)) * steps : ((v - o.min) / (o.max - o.min)) * steps);
    const fromPos = (p) => {
      const raw = log ? o.min * (o.max / o.min) ** (p / steps) : o.min + (o.max - o.min) * p / steps;
      const step = o.step || 0;
      return step ? +(Math.round(raw / step) * step).toFixed(6) : +raw.toPrecision(4);
    };
    const root = el("div", { class: "ctl" });
    root.innerHTML = `<div class="ctl-h"><label>${o.label}</label>${o.sym ? `<span class="sym">${o.sym}</span>` : ""}<span class="spacer"></span>` +
      `<span class="lock" hidden></span><div class="numbox"><input type="number" step="any"><span>${o.unit || ""}</span></div></div>` +
      `<input type="range" min="0" max="${steps}" step="1">` +
      (o.scale ? `<div class="range-scale">${o.scale.map((s) => `<span>${s}</span>`).join("")}</div>` : "");
    const range = root.querySelector("input[type=range]"), box = root.querySelector("input[type=number]");
    const wrap = root.querySelector(".numbox"), lock = root.querySelector(".lock");
    let value = o.value, locked = false;
    const digits = o.digits ?? 2;
    function paint() {
      range.value = String(clamp(toPos(value), 0, steps));
      range.style.setProperty("--fill", `${(range.value / steps) * 100}%`);
      if (document.activeElement !== box) box.value = (+value.toFixed(digits)).toString();
    }
    function set(v, emit) {
      value = v; wrap.classList.remove("invalid"); paint();
      if (emit && o.onChange) o.onChange(value);
    }
    range.addEventListener("input", () => set(fromPos(+range.value), true));
    function commit() {
      const v = +box.value;
      if (box.value === "" || !Number.isFinite(v) || v < o.min || v > o.max) {
        wrap.classList.add("invalid");
        toast(`${o.label} 需在 ${o.min}–${o.max} ${o.unit || ""} 内`);
        return;
      }
      box.blur(); set(v, true);
    }
    box.addEventListener("keydown", (e) => {
      if (e.key === "Enter") commit();
      if (e.key === "Escape") { box.value = String(value); box.blur(); }
    });
    box.addEventListener("change", commit);
    box.addEventListener("blur", () => { if (!wrap.classList.contains("invalid")) box.value = (+value.toFixed(digits)).toString(); });
    paint();
    return {
      node: root, get: () => value, set: (v) => set(v, false),
      lock(text) {
        locked = !!text; lock.hidden = !locked; lock.textContent = text || "";
        range.disabled = box.disabled = locked;
      },
      get locked() { return locked; },
      range(min, max) { o.min = min; o.max = max; set(clamp(value, min, max), false); },
    };
  }

  function seg(options, value, onChange, small) {
    const root = el("div", { class: `seg${small ? " small" : ""}` });
    let current = value;
    options.forEach((op) => {
      const b = el("button", { type: "button", "data-v": String(op.value) }, `${op.color ? `<i class="sw" style="background:${op.color}"></i>` : ""}${op.label}`);
      b.addEventListener("click", () => { if (current !== op.value) { set(op.value); onChange(op.value); } });
      root.appendChild(b);
    });
    function set(v) {
      current = v;
      root.querySelectorAll("button").forEach((b) => b.classList.toggle("on", b.dataset.v === String(v)));
    }
    set(value);
    return { node: root, set, get: () => current };
  }

  function chips(items, onPick) {
    const root = el("div", { class: "chips" });
    items.forEach((it) => {
      const b = el("button", { type: "button", class: `chip${it.danger ? " danger" : ""}`, title: it.title || "" }, it.label);
      b.addEventListener("click", () => onPick(it));
      root.appendChild(b);
    });
    return root;
  }

  /* KPI tiles keyed by id; set(id, html, detail, off) updates one tile. */
  function kpis(defs) {
    const root = el("div", { class: "kpis" });
    const tiles = {};
    defs.forEach((d) => {
      const t = el("div", { class: "kpi loading", style: d.color ? `--kc:${d.color}` : "", title: d.tip || "" },
        `<div class="k">${d.label}${d.sym ? `<i>${d.sym}</i>` : ""}</div><div class="v">—</div><div class="d">${d.detail || "&nbsp;"}</div>` +
        (d.gauge ? `<div class="gauge"><b></b><i></i></div>` : ""));
      tiles[d.id] = t; root.appendChild(t);
    });
    return {
      node: root,
      set(id, value, unit, detail, off) {
        const t = tiles[id];
        t.classList.remove("loading"); t.classList.toggle("off", !!off);
        t.querySelector(".v").innerHTML = `${value}${unit ? `<small>${unit}</small>` : ""}`;
        if (detail !== undefined) t.querySelector(".d").innerHTML = detail || "&nbsp;";
      },
      gauge(id, fraction, mark, color) {
        const g = tiles[id].querySelector(".gauge");
        g.querySelector("b").style.width = `${clamp(fraction, 0, 1) * 100}%`;
        g.querySelector("b").style.background = color;
        g.querySelector("i").style.left = `${mark * 100}%`;
      },
      tile: (id) => tiles[id],
    };
  }

  function card(title, sub, body, extra) {
    const c = el("section", { class: "card" });
    c.innerHTML = `<div class="card-h"><h3>${title}</h3>${sub ? `<span class="sub">${sub}</span>` : ""}<span class="spacer"></span>${extra || ""}</div>`;
    const b = el("div", { class: "card-b" });
    if (typeof body === "string") b.innerHTML = body; else if (body) b.appendChild(body);
    c.appendChild(b);
    return c;
  }

  function banner(node, kind, icon, html, src) {
    node.className = `banner ${kind}`;
    node.innerHTML = `<div class="ic">${icon}</div><div class="msg">${html}${src ? `<span class="src">${esc(src)}</span>` : ""}</div>`;
  }

  function strip(items) {
    return `<div class="strip">${items.map(([k, v]) => `<div><div class="k">${k}</div><div class="v">${v}</div></div>`).join("")}</div>`;
  }

  /* guide = {input:[...], output:[...], steps:[...]} renders a collapsible
   * "how to use" strip; exporter() returns {inputs, outputs} for JSON export. */
  function view(id, title, sub, guide, exporter) {
    const v = el("section", { class: "view", id: `view-${id}` });
    v.innerHTML = `<div class="view-head"><div><h1>${title}</h1><p>${sub}</p></div><span class="spacer"></span></div>`;
    const head = v.querySelector(".view-head");
    if (guide) {
      const key = `rp-guide-${id}`;
      let open = true;
      try { open = localStorage.getItem(key) !== "0"; } catch (e) { open = true; }
      const box = el("div", { class: "guide" },
        `<div><b>① 输入</b><ul>${guide.input.map((x) => `<li>${x}</li>`).join("")}</ul></div>` +
        `<div><b>② 输出</b><ul>${guide.output.map((x) => `<li>${x}</li>`).join("")}</ul></div>` +
        `<div><b>③ 操作</b><ul>${guide.steps.map((x) => `<li>${x}</li>`).join("")}</ul></div>`);
      box.hidden = !open;
      const btn = el("button", { class: "btn", type: "button", title: "显示/隐藏本页输入输出说明" }, "使用说明");
      btn.classList.toggle("on", open);
      btn.addEventListener("click", () => {
        box.hidden = !box.hidden; btn.classList.toggle("on", !box.hidden);
        try { localStorage.setItem(key, box.hidden ? "0" : "1"); } catch (e) { /* optional */ }
      });
      head.appendChild(btn);
      head.after(box);
    }
    if (exporter) {
      const btn = el("button", { class: "btn", type: "button", title: "下载当前输入与 C 输出（JSON）" }, "导出结果");
      btn.addEventListener("click", () => {
        const data = exporter();
        if (!data) { toast("暂无可导出的结果"); return; }
        const blob = new Blob([JSON.stringify({ program: "rocketperf-gui", view: id, exported_at: new Date().toISOString(), ...data }, null, 2)], { type: "application/json" });
        const a = el("a", { href: URL.createObjectURL(blob), download: `rocketperf-${id}-${Date.now()}.json` });
        document.body.appendChild(a); a.click(); a.remove();
        toast("已导出当前输入与输出");
      });
      head.appendChild(btn);
    }
    $("views").appendChild(v);
    return v;
  }
  return { slider, seg, chips, kpis, card, banner, strip, view };
})();
