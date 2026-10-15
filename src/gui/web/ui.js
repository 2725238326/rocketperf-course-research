"use strict";
/* Page scaffolding and controls shared by every tab. */
function h(tag, cls, html) {
  const e = document.createElement(tag);
  if (cls) e.className = cls;
  if (html !== undefined) e.innerHTML = html;
  return e;
}
function view(id) {
  const section = h("section", "view");
  section.id = `v-${id}`; section.setAttribute("role", "tabpanel"); section.hidden = true;
  const rail = h("div", "rail"), stage = h("div", "stage");
  section.append(rail, stage); $("main").append(section);
  return { section, rail, stage };
}
function card(parent, title, html, cls = "") {
  const c = h("div", `card ${cls}`, (title ? `<h2>${title}</h2>` : "") + (html || ""));
  parent.append(c); return c;
}
const badge = (cls, text) => `<span class="badge ${cls}">${text}</span>`;

let uid = 0;
/* Continuous slider with a typed value box. o: {label, min, max, step, value, unit, digits, ticks, color}.
 * The physics domain stays in C; the box only rejects non-numbers and values off the slider scale. */
function slider(parent, o) {
  const id = `s${++uid}`, w = h("div", "ctl"), steps = Math.round((o.max - o.min) / o.step), d = o.digits ?? 2;
  w.innerHTML = `<div class="ctl-head"><label for="${id}">${o.label}</label><span class="val"><input class="num" type="number" step="any" aria-label="数值">` +
    `<span class="unit">${o.unit || ""}</span></span></div><input type="range" id="${id}" min="0" max="${steps}" step="1"><div class="ticks"></div>`;
  parent.append(w);
  const input = w.querySelector("input[type=range]"), box = w.querySelector("input.num"), handlers = [];
  input.style.setProperty("--c", o.color || "var(--blue)");
  w.querySelector(".ticks").innerHTML = (o.ticks || [o.min, o.max]).map((t) => `<span>${t}</span>`).join("");
  let value = o.value;
  const snap = (v) => +(Math.round((v - o.min) / o.step) * o.step + o.min).toFixed(6);
  const paint = () => {
    const pos = clamp(Math.round((value - o.min) / o.step), 0, steps);
    input.value = pos; input.style.setProperty("--p", `${(100 * pos) / steps}%`);
    if (document.activeElement !== box) box.value = (+value.toFixed(d)).toString();
    box.classList.remove("invalid");
  };
  const api = {
    get: () => value,
    set(v, quiet) { value = v; paint(); if (!quiet) handlers.forEach((f) => f(value)); },
    on(f) { handlers.push(f); return api; },
    lock(text) {
      w.classList.toggle("locked", !!text); box.disabled = !!text;
      let tag = w.querySelector(".lock");
      if (text && !tag) { tag = h("span", "lock"); w.querySelector("label").after(tag); }
      if (tag) { tag.textContent = text || ""; tag.hidden = !text; }
    },
  };
  input.addEventListener("input", () => api.set(snap(o.min + +input.value * o.step)));
  const commit = () => {
    const v = +box.value;
    if (box.value === "" || !Number.isFinite(v) || v < o.min || v > o.max) { box.classList.add("invalid"); toast(`${o.name || "数值"}需在 ${o.min}–${o.max} 内`); return; }
    box.blur(); api.set(v);
  };
  box.addEventListener("keydown", (e) => { if (e.key === "Enter") commit(); if (e.key === "Escape") { box.value = String(value); box.blur(); } });
  box.addEventListener("change", commit);
  paint();
  return api;
}
function seg(parent, label, items, value) {
  const w = h("div", "ctl", label ? `<div class="ctl-head"><span>${label}</span></div>` : ""), box = h("div", "seg");
  box.setAttribute("role", "group"); if (label) box.setAttribute("aria-label", label);
  w.append(box); parent.append(w);
  const handlers = []; let cur = value;
  const api = {
    get: () => cur,
    set(v, quiet) { cur = v; [...box.children].forEach((b, i) => b.setAttribute("aria-pressed", String(items[i][0] === v))); if (!quiet) handlers.forEach((f) => f(v)); },
    on(f) { handlers.push(f); return api; }, el: w,
  };
  for (const [v, text] of items) {
    const b = h("button", "", text); b.type = "button";
    b.addEventListener("click", () => api.set(v)); box.append(b);
  }
  api.set(value, true);
  return api;
}
function presets(parent, items) {
  const w = h("div", "presets");
  for (const [text, fn, title] of items) {
    const b = h("button", "", text); b.type = "button"; if (title) b.title = title;
    b.addEventListener("click", fn); w.append(b);
  }
  parent.append(w);
  return w;
}
function checkbox(parent, label, checked) {
  const w = h("label", "check", `<input type="checkbox"${checked ? " checked" : ""}>${label}`);
  parent.append(w); return w.querySelector("input");
}

/* KPI card: values tween when the card keeps its shape. */
function kpiRow(parent, n) { const r = h("div", "kpis"); r.style.setProperty("--n", n); parent.append(r); return r; }
function kpi(row, label, hint = "") {
  const el = h("div", "kpi", `<div class="k"><b>${label}</b><span>${hint}</span></div><div class="b"><div class="v">—</div></div><div class="f">&nbsp;</div>`);
  row.append(el);
  const body = el.querySelector(".b"), foot = el.querySelector(".f");
  let mode = "";
  const num = (v, d, unit, cls = "") => `<div class="v ${cls}"><span class="n" data-v="${v}">${fx(v, d)}</span><small>${unit || ""}</small></div>`;
  return {
    el,
    set(o) {
      const m = o.refused ? "r" : o.pair ? "p" : o.html ? "h" : "s";
      if (m === "r") body.innerHTML = `<div class="refused">✕ ${o.refused}</div>`;
      else if (m === "h") body.innerHTML = o.html;
      else if (m !== mode) body.innerHTML = m === "p" ? `<div class="pair">${o.pair.map((p) => num(p.v, p.d, p.unit, p.cls)).join("")}</div>` : num(o.v, o.d, o.unit, o.cls);
      else {
        const spans = body.querySelectorAll(".n"), vals = m === "p" ? o.pair : [o];
        vals.forEach((p, i) => { if (Number.isFinite(p.v)) tween(spans[i], p.v, (x) => fx(x, p.d)); else spans[i].textContent = "—"; });
      }
      mode = m; foot.innerHTML = o.foot || "&nbsp;";
    },
  };
}

/* Computation chain strip: the C call sequence for the current selection. */
function chain(parent, label) {
  const el = h("div", "chain"); parent.append(el);
  return { set(steps) {
    el.innerHTML = `<span class="label">${label}</span>` + steps.map((s) =>
      `<span class="step ${s.state || "ok"}"><b>${s.name}</b>${s.val ? `<em>${s.val}</em>` : ""}</span>`).join('<span class="arrow">→</span>');
  } };
}
function evidence(parent, title = "求解器证据") {
  const c = card(parent, "", `<h3>${title}</h3><table></table><div class="cmd"><button type="button">复制</button><span></span></div>`, "ev");
  const table = c.querySelector("table"), cmd = c.querySelector(".cmd span");
  c.querySelector("button").addEventListener("click", () => copyText(cmd.textContent));
  return { set(rows, text) {
    table.innerHTML = rows.map(([k, v]) => `<tr><td>${k}</td><td>${v}</td></tr>`).join("");
    cmd.textContent = text;
  } };
}
function figure(parent, o) {
  const f = h("div", "fig", `<div class="fig-head"><h3>${o.title}</h3><p>${o.sub || ""}</p></div>` +
    (o.legend ? `<div class="legend">${o.legend}</div>` : "") + `<div class="plot"></div>`);
  parent.append(f);
  return { el: f, body: f.querySelector(".plot"), head: f.querySelector(".fig-head"), sub: f.querySelector(".fig-head p"), legend: f.querySelector(".legend") };
}
function figs(parent, columns, rows) {
  const g = h("div", "figs"); g.style.gridTemplateColumns = columns; if (rows) g.style.gridTemplateRows = rows;
  parent.append(g); return g;
}
function takeaway(parent) { const t = h("div", "take"); parent.append(t); return t; }
const legendItem = (color, text, sq) => `<span><i class="${sq ? "sq" : ""}" style="background:${color}"></i>${text}</span>`;
/* Placeholder inside a plot while the C reply is pending or refused. */
function plotMessage(api, text, color = "#7A8496") {
  api.content.innerHTML = el("text", { x: api.w / 2, y: api.h / 2, "text-anchor": "middle", fill: color, "font-size": 13 }, text);
  api.state = null;
}
