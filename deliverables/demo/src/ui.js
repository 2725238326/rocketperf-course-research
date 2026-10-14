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
function slider(parent, o) {
  const id = `s${++uid}`, w = h("div", "ctl");
  w.innerHTML = `<div class="ctl-head"><label for="${id}">${o.label}</label><output for="${id}"></output></div>` +
    `<input type="range" id="${id}" min="0" max="${o.values.length - 1}" step="1"><div class="ticks"></div>`;
  parent.append(w);
  const input = w.querySelector("input"), out = w.querySelector("output"), handlers = [];
  input.style.setProperty("--c", o.color || "var(--blue)");
  const fmt = o.fmt || ((v) => v);
  w.querySelector(".ticks").innerHTML = (o.ticks || [o.values[0], o.values[o.values.length - 1]]).map((t) => `<span>${fmt(t)}</span>`).join("");
  const sync = () => {
    const v = o.values[+input.value];
    out.textContent = fmt(v); input.setAttribute("aria-valuetext", fmt(v));
    input.style.setProperty("--p", `${(100 * +input.value) / Math.max(1, o.values.length - 1)}%`);
  };
  const api = {
    get: () => o.values[+input.value],
    set(v, quiet) {
      let i = o.values.findIndex((x) => Math.abs(x - v) < 1e-9);
      if (i < 0) i = o.values.reduce((b, x, j) => (Math.abs(x - v) < Math.abs(o.values[b] - v) ? j : b), 0);
      input.value = i; sync(); if (!quiet) handlers.forEach((f) => f(api.get()));
    },
    on(f) { handlers.push(f); return api; }, input,
  };
  input.addEventListener("input", () => { sync(); handlers.forEach((f) => f(api.get())); });
  api.set(o.value, true);
  return api;
}
function seg(parent, label, items, value) {
  const w = h("div", "ctl", `<div class="ctl-head"><span>${label}</span></div>`), box = h("div", "seg");
  box.setAttribute("role", "group"); box.setAttribute("aria-label", label);
  w.append(box); parent.append(w);
  const handlers = []; let cur = value;
  const api = {
    get: () => cur,
    set(v, quiet) { cur = v; [...box.children].forEach((b, i) => b.setAttribute("aria-pressed", String(items[i][0] === v))); if (!quiet) handlers.forEach((f) => f(v)); },
    on(f) { handlers.push(f); return api; },
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
}
function checkbox(parent, label, checked) {
  const w = h("label", "check", `<input type="checkbox"${checked ? " checked" : ""}>${label}`);
  parent.append(w); return w.querySelector("input");
}

/* KPI card: values tween when the card keeps its shape. */
function kpiRow(parent, n) { const r = h("div", "kpis"); r.style.setProperty("--n", n); parent.append(r); return r; }
function kpi(row, label, hint = "") {
  const el = h("div", "kpi", `<div class="k"><b>${label}</b><span>${hint}</span></div><div class="b"></div><div class="f"></div>`);
  row.append(el);
  const body = el.querySelector(".b"), foot = el.querySelector(".f");
  let mode = "";
  const num = (v, d, unit, cls = "") => `<div class="v ${cls}"><span class="n" data-v="${v}">${fx(v, d)}</span><small>${unit || ""}</small></div>`;
  return {
    el,
    set(o) {
      const m = o.refused ? "r" : o.pair ? "p" : o.html ? "h" : "s";
      if (m === "r") { body.innerHTML = `<div class="refused">✕ ${o.refused}</div>`; }
      else if (m === "h") { body.innerHTML = o.html; }
      else if (m !== mode) {
        body.innerHTML = m === "p" ? `<div class="pair">${o.pair.map((p) => num(p.v, p.d, p.unit, p.cls)).join("")}</div>` : num(o.v, o.d, o.unit, o.cls);
      } else {
        const spans = body.querySelectorAll(".n"), vals = m === "p" ? o.pair : [o];
        vals.forEach((p, i) => { if (Number.isFinite(p.v)) tween(spans[i], p.v, (x) => fx(x, p.d)); else spans[i].textContent = "—"; });
      }
      mode = m; foot.innerHTML = o.foot || "";
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
  return { el: f, body: f.querySelector(".plot"), sub: f.querySelector(".fig-head p"), legend: f.querySelector(".legend") };
}
function figs(parent, columns, rows) {
  const g = h("div", "figs"); g.style.gridTemplateColumns = columns; if (rows) g.style.gridTemplateRows = rows;
  parent.append(g); return g;
}
function takeaway(parent) { const t = h("div", "take"); parent.append(t); return t; }
const legendItem = (color, text, sq) => `<span><i class="${sq ? "sq" : ""}" style="background:${color}"></i>${text}</span>`;
