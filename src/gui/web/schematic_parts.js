/* Engine components as SVG strings. Geometry is schematic except nozzle throat/exit,
 * which are drawn at the computed throat area and area ratio (one px-per-metre scale). */
const COL = { ch4: "#0F8A8A", rp1: "#C8741E", lox: "#2F6FD1", gas: "#C2412D", shaft: "#66758C" };
/* Gradients live once in #defs (always rendered); per-schematic copies would collide by id
 * and resolve into hidden tabs, which Chromium does not paint. */
function schematicDefs() {
  if (!document.getElementById("g-metal")) document.getElementById("defs").innerHTML = schematicDefsMarkup();
  return "";
}
function schematicDefsMarkup() {
  const lin = (id, stops, v) => `<linearGradient id="${id}" x1="0" y1="0" x2="${v ? 0 : 1}" y2="${v ? 1 : 0}">` +
    stops.map(([o, c, a]) => `<stop offset="${o}" stop-color="${c}"${a !== undefined ? ` stop-opacity="${a}"` : ""}/>`).join("") + "</linearGradient>";
  return "<defs>" +
    lin("g-metal", [[0, "#8E9AAD"], [0.32, "#F1F4F8"], [0.58, "#C9D1DC"], [1, "#77839A"]]) +
    lin("g-casing", [[0, "#6F7C92"], [0.4, "#DCE3EC"], [1, "#5F6B80"]]) +
    lin("g-copper", [[0, "#7A4A2E"], [0.35, "#E2B086"], [0.6, "#C48455"], [1, "#6A3E26"]]) +
    lin("g-hotsteel", [[0, "#7C6A63"], [0.4, "#E8D9D0"], [1, "#6E5A52"]]) +
    lin("g-ch4", [[0, "#2BB3B0"], [1, "#0B6E6E"]], true) +
    lin("g-rp1", [[0, "#E9A04E"], [1, "#A85F16"]], true) +
    lin("g-lox", [[0, "#6FA3F0"], [1, "#1E55B5"]], true) +
    lin("g-plume", [[0, "#FFF6DA"], [0.18, "#FFD07A"], [0.55, "#FF8A3D", 0.6], [1, "#FF6A2E", 0]], true) +
    `<radialGradient id="g-glow" cx="0.5" cy="0.55" r="0.55"><stop offset="0" stop-color="#FFF1B8"/><stop offset="0.45" stop-color="#FFA24A" stop-opacity="0.85"/><stop offset="1" stop-color="#C2412D" stop-opacity="0"/></radialGradient>` +
    "</defs>";
}
const capsule = (x, y, w, hgt) => { const r = w / 2; return `M${x},${y + r}A${r},${r} 0 0 1 ${x + w},${y + r}V${y + hgt - r}A${r},${r} 0 0 1 ${x},${y + hgt - r}Z`; };
const label = (x, y, name, sub, anchor = "start") =>
  el("text", { x, y, class: "name", "text-anchor": anchor }, name) + (sub ? el("text", { x, y: y + 17, class: "sub", "text-anchor": anchor }, sub) : "");

function tank(o) {
  const { x, y, w, h: hh, key, fluid } = o, level = y + w / 2 + 8, inner = capsule(x + 5, y + 5, w - 10, hh - 10);
  let s = `<g class="comp" data-key="${key}">` + el("path", { d: capsule(x - 6, y - 6, w + 12, hh + 12), class: "halo", fill: "none", stroke: "#8DB4F0", "stroke-width": 6, "stroke-opacity": 0.5 });
  const cid = `clip-${key}-${++uid}`;
  s += `<clipPath id="${cid}"><path d="${inner}"/></clipPath>`;
  s += el("path", { d: capsule(x, y, w, hh), class: "outline", fill: "url(#g-metal)", stroke: "#56637A", "stroke-width": 1.6 });
  s += `<g clip-path="url(#${cid})">` + el("rect", { x, y, width: w, height: hh, fill: "#EEF2F7" });
  s += el("rect", { x, y: level, width: w, height: y + hh - level, fill: `url(#g-${fluid})` });
  s += `<path class="wave" d="M${x - 12},${level} q6,-4 12,0 t12,0 t12,0 t12,0 t12,0 t12,0 t12,0 t12,0 t12,0 t12,0 t12,0 V${level + 8} H${x - 12}Z" fill="${COL[fluid]}" opacity="0.55"/>`;
  s += el("rect", { x: x + w * 0.16, y, width: w * 0.09, height: hh, fill: "#fff", opacity: 0.22 }) + "</g>";
  for (const yy of [y + w / 2, y + hh - w / 2]) s += el("line", { x1: x + 3, x2: x + w - 3, y1: yy, y2: yy, stroke: "#56637A", "stroke-opacity": 0.35 });
  s += el("rect", { x: x + w / 2 - 9, y: y + hh - 2, width: 18, height: 10, fill: "url(#g-casing)", stroke: "#56637A" });
  s += el("text", { x: x + w / 2, y: y + w / 2 - 4, class: "name", "text-anchor": "middle" }, o.name);
  o.lines.forEach((t, i) => { s += el("text", { x: x + w / 2, y: level + 24 + i * 17, "text-anchor": "middle", "font-size": 12.5, fill: "#fff", "font-weight": i ? 400 : 650 }, t); });
  return s + "</g>";
}

function pump(o) {
  const { cx, cy, r, key, fluid } = o;
  let s = `<g class="comp" data-key="${key}">` + el("circle", { cx, cy, r: r + 8, class: "halo", fill: "none", stroke: "#8DB4F0", "stroke-width": 6, "stroke-opacity": 0.5 });
  s += el("rect", { x: cx + r * 0.25, y: cy - r * 0.28, width: r * 0.8, height: r * 0.56, fill: "url(#g-casing)", stroke: "#56637A" });
  s += el("rect", { x: cx - r * 1.05, y: cy - r * 0.24, width: r * 0.6, height: r * 0.48, fill: "url(#g-casing)", stroke: "#56637A" });
  s += el("circle", { cx, cy, r, class: "outline", fill: "url(#g-casing)", stroke: "#56637A", "stroke-width": 1.6 });
  s += el("circle", { cx, cy, r: r * 0.78, fill: "#F7F9FC", stroke: "#8693A8" });
  let blades = "";
  for (let i = 0; i < 7; i++) {
    const a = (i * 2 * Math.PI) / 7, r0 = r * 0.2, r1 = r * 0.72;
    const p0 = [cx + r0 * Math.cos(a), cy + r0 * Math.sin(a)], p1 = [cx + r1 * Math.cos(a + 0.9), cy + r1 * Math.sin(a + 0.9)];
    const c = [cx + r * 0.62 * Math.cos(a + 0.2), cy + r * 0.62 * Math.sin(a + 0.2)];
    blades += `<path d="M${p0[0].toFixed(1)},${p0[1].toFixed(1)}Q${c[0].toFixed(1)},${c[1].toFixed(1)} ${p1[0].toFixed(1)},${p1[1].toFixed(1)}" stroke="${COL[fluid]}" stroke-width="3" fill="none" stroke-linecap="round"/>`;
  }
  s += `<g class="spin">${el("circle", { cx, cy, r: r * 0.74, fill: "none", stroke: "none" })}${blades}${el("circle", { cx, cy, r: r * 0.2, fill: COL[fluid] })}</g>`;
  return s + el("circle", { cx, cy, r: r * 0.08, fill: "#fff" }) + "</g>";
}

function turbine(o) {
  const { cx, cy, r, key } = o;
  let s = `<g class="comp" data-key="${key}">` + el("circle", { cx, cy, r: r + 8, class: "halo", fill: "none", stroke: "#8DB4F0", "stroke-width": 6, "stroke-opacity": 0.5 });
  for (const [x, y] of o.flanges) s += el("rect", { x: x - 11, y: y - 11, width: 22, height: 22, rx: 3, fill: "url(#g-hotsteel)", stroke: "#6E5A52" });
  s += el("circle", { cx, cy, r, class: "outline", fill: "url(#g-hotsteel)", stroke: "#6E5A52", "stroke-width": 1.6 });
  s += el("circle", { cx, cy, r: r * 0.86, fill: "#2B2F3A" });
  let blades = "";
  for (let i = 0; i < 30; i++) {
    const a = (i * 2 * Math.PI) / 30, r0 = r * 0.5, r1 = r * 0.84;
    blades += `<line x1="${(cx + r0 * Math.cos(a)).toFixed(1)}" y1="${(cy + r0 * Math.sin(a)).toFixed(1)}" x2="${(cx + r1 * Math.cos(a + 0.12)).toFixed(1)}" y2="${(cy + r1 * Math.sin(a + 0.12)).toFixed(1)}" stroke="#E7B98F" stroke-width="2"/>`;
  }
  s += `<g class="spin">${el("circle", { cx, cy, r: r * 0.84, fill: "none" })}${blades}${el("circle", { cx, cy, r: r * 0.48, fill: "url(#g-hotsteel)", stroke: "#6E5A52" })}</g>`;
  return s + el("circle", { cx, cy, r: r * 0.12, fill: "#56637A" }) + "</g>";
}

function shaft(x, y0, y1) {
  return el("rect", { x: x - 7, y: y0, width: 14, height: y1 - y0, rx: 4, fill: "url(#g-metal)", stroke: "#56637A" }) +
    el("line", { x1: x, x2: x, y1: y0 + 4, y2: y1 - 4, class: "shaft-run", stroke: "#fff", "stroke-width": 3, "stroke-opacity": 0.7 });
}

/* Vertical chamber + bell. rt/re in px from the computed throat area; plume follows pe/pa. */
function engine(o) {
  const { cx, top, rc, rt, re, key } = o, y1 = top + o.lc, yt = y1 + rc * 1.15, ye = yt + o.ln;
  const half = (sx) => `L${cx + sx * rc},${y1}C${cx + sx * rc},${y1 + rc * 0.6} ${cx + sx * rt * 1.05},${yt - rt * 0.5} ${cx + sx * rt},${yt}` +
    `C${cx + sx * rt * 1.8},${yt + o.ln * 0.22} ${cx + sx * re * 0.97},${ye - o.ln * 0.42} ${cx + sx * re},${ye}`;
  const outline = `M${cx - rc},${top}H${cx + rc}` + half(1) + `H${cx - re}` +
    `C${cx - re * 0.97},${ye - o.ln * 0.42} ${cx - rt * 1.8},${yt + o.ln * 0.22} ${cx - rt},${yt}` +
    `C${cx - rt * 1.05},${yt - rt * 0.5} ${cx - rc},${y1 + rc * 0.6} ${cx - rc},${y1}Z`;
  let s = `<g class="comp" data-key="${key}">` + el("path", { d: outline, class: "halo", fill: "none", stroke: "#8DB4F0", "stroke-width": 10, "stroke-opacity": 0.5 });
  const plumeLen = o.plume, under = o.pe > o.pa, w1 = under ? re * 1.25 : re * 0.82;
  if (plumeLen > 0) {
    s += `<path class="flicker" d="M${cx - re},${ye}C${cx - w1},${ye + plumeLen * 0.4} ${cx - w1 * 0.85},${ye + plumeLen * 0.8} ${cx - w1 * 0.55},${ye + plumeLen}H${cx + w1 * 0.55}C${cx + w1 * 0.85},${ye + plumeLen * 0.8} ${cx + w1},${ye + plumeLen * 0.4} ${cx + re},${ye}Z" fill="url(#g-plume)"/>`;
    if (o.pa > 0) for (let i = 1; i <= 3; i++) {
      const yy = ye + plumeLen * (0.12 + 0.24 * i), ww = re * (0.42 - 0.07 * i);
      s += el("path", { d: `M${cx},${yy - 14}L${cx + ww},${yy}L${cx},${yy + 14}L${cx - ww},${yy}Z`, fill: "#FFF7E0", opacity: 0.75 - 0.15 * i });
    }
  }
  const cid = `clip-${key}-${++uid}`;
  s += `<clipPath id="${cid}"><path d="${outline}"/></clipPath>`;
  s += el("path", { d: outline, class: "outline", fill: "url(#g-copper)", stroke: "#5A3520", "stroke-width": 1.6 });
  let tubes = "";
  for (let x = cx - re; x <= cx + re; x += 5) tubes += `M${x},${top}V${ye}`;
  s += `<g clip-path="url(#${cid})">${el("path", { d: tubes, stroke: "#5A3520", "stroke-opacity": 0.22, "stroke-width": 1 })}` +
    el("ellipse", { cx, cy: y1 + rc * 0.25, rx: rc * 0.72, ry: rc * 0.7, fill: "url(#g-glow)", class: "flicker" }) + "</g>";
  s += el("rect", { x: cx - rc - 8, y: top - 16, width: 2 * rc + 16, height: 16, rx: 3, fill: "url(#g-casing)", stroke: "#56637A" });
  s += el("line", { x1: cx - rt, x2: cx + rt, y1: yt, y2: yt, stroke: "#fff", "stroke-opacity": 0.7, "stroke-dasharray": "3 3" });
  (o.lines || []).forEach((t, i) => { s += el("text", { x: cx, y: top + 30 + i * 18, "text-anchor": "middle", "font-size": i ? 12.5 : 14.5, "font-weight": i ? 600 : 700, fill: "#3A1F10" }, t); });
  return { svg: s + "</g>", throatY: yt, exitY: ye };
}

function preburner(o) {
  const { x, y, key } = o, len = 84, r = 22;
  let s = `<g class="comp" data-key="${key}">` + el("rect", { x: x - 8, y: y - r - 8, width: len + 26, height: 2 * r + 16, rx: 14, class: "halo", fill: "none", stroke: "#8DB4F0", "stroke-width": 6, "stroke-opacity": 0.5 });
  const body = `M${x + len},${y - r}H${x + 22}C${x + 8},${y - r} ${x + 6},${y - 9} ${x - 4},${y - 9}V${y + 9}C${x + 6},${y + 9} ${x + 8},${y + r} ${x + 22},${y + r}H${x + len}Z`;
  s += el("path", { d: body, class: "outline", fill: "url(#g-hotsteel)", stroke: "#6E5A52", "stroke-width": 1.6 });
  s += el("ellipse", { cx: x + 52, cy: y, rx: 26, ry: r * 0.62, fill: "url(#g-glow)", class: "flicker" });
  s += el("rect", { x: x + len, y: y - r - 2, width: 12, height: 2 * r + 4, rx: 2, fill: "url(#g-casing)", stroke: "#56637A" });
  return s + "</g>";
}

/* Pipe with a white casing so a later pipe visibly passes over an earlier one. */
function route(pts, radius = 12) {
  let d = `M${pts[0][0]},${pts[0][1]}`;
  for (let i = 1; i < pts.length - 1; i++) {
    const [x0, y0] = pts[i - 1], [x1, y1] = pts[i], [x2, y2] = pts[i + 1];
    const d1 = Math.hypot(x1 - x0, y1 - y0), d2 = Math.hypot(x2 - x1, y2 - y1), rr = Math.min(radius, d1 / 2, d2 / 2);
    d += `L${x1 - ((x1 - x0) / d1) * rr},${y1 - ((y1 - y0) / d1) * rr}Q${x1},${y1} ${x1 + ((x2 - x1) / d2) * rr},${y1 + ((y2 - y1) / d2) * rr}`;
  }
  const [xn, yn] = pts[pts.length - 1];
  return d + `L${xn},${yn}`;
}
const pipeWidth = (kg) => 2.4 + 1.05 * Math.sqrt(kg);
function pipe(pts, color, kg) {
  const w = pipeWidth(kg), d = route(pts);
  return el("path", { d, fill: "none", stroke: "#fff", "stroke-width": w + 7, "stroke-linejoin": "round" }) +
    el("path", { d, fill: "none", stroke: color, "stroke-width": w, "stroke-linejoin": "round" }) +
    el("path", { d, class: "flow", fill: "none", stroke: "#fff", "stroke-width": Math.max(1.6, w * 0.34), "stroke-opacity": 0.9 });
}
function pill(x, y, text, color) {
  const w = textWidth(text) * 1.05 + 14;
  return `<g class="pill">${el("rect", { x: x - w / 2, y: y - 10.5, width: w, height: 21, rx: 10.5, stroke: color })}${el("text", { x, y: y + 4.5, "text-anchor": "middle", fill: color }, text)}</g>`;
}
