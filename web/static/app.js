/* Wursta Agent Hive — vanilla JS UI. Catalog from /api/catalog; live runs stream from /api/run (SSE). */
"use strict";

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const SQ3 = Math.sqrt(3);
const R = 42; // hex radius in px

const S = {
  cat: null, raw: null, agents: new Map(), realmOf: new Map(), view: "hive",
  filters: { q: "", status: new Set(), tier: new Set() },
  open: null, sessions: new Map(), running: false, files: [], warm: new Map(),
  me: null, auth: null, ran: new Set(), rated: new Set(), sample: false,
};
/* If an admin closes this session (or blocks the account), the next API call answers 401: back to sign-in. */
const _fetch = window.fetch.bind(window);
window.fetch = async (...args) => {
  const r = await _fetch(...args);
  const url = String(args[0] instanceof Request ? args[0].url : args[0]);
  if (r.status === 401 && S.me && url.includes("/api/") && !url.includes("/api/auth/")) location.reload();
  return r;
};
const SHOWCASE = () => S.cat && S.cat.edition && S.cat.edition !== "internal";
const TERM = () => t("term." + ((S.cat && S.cat.term) || "realm"));

const STATUS_ORDER = ["demo_ready", "built", "in_build", "library"];
const TIER_LABEL = { lite: "Flash-Lite", flash: "Flash", argon: "Argon" };
const BLOCK_COLORS = { model: "#8a3fd0", runtime: "#13906a", tools: "#2b6fd0", grounding: "#e39a1c" };
const LAYER_COLORS = { google_security: "#1a73e8", waisentry: "#d93a40" };
const SHIELD = `<svg class="shield" viewBox="0 0 24 24" aria-hidden="true"><path d="M12 3l7 3v5c0 4.6-3 8.4-7 10-4-1.6-7-5.4-7-10V6z"/><path d="M9 12l2 2 4-4"/></svg>`;
const CHEV = `<svg class="chev" viewBox="0 0 24 24" aria-hidden="true"><path d="M6 9l6 6 6-6"/></svg>`;
const layersFor = (realmId) => (S.cat.security_layers || []).filter((l) => l.realms.includes(realmId));
const firstSentence = (t) => (String(t).match(/^.*?[.!?](\s|$)/) || [t])[0].trim();

/* A realm's security layer: one compact band; click to expand the controls. */
function securityBand(realmId) {
  return layersFor(realmId).map((l) => {
    const color = LAYER_COLORS[l.id] || "#5f5d57";
    const label = l.id === "waisentry" ? t("sec.waisentry") : t("sec.layer");
    const open = l.id === "waisentry" && S.agents.has("waisentry")
      ? `<button class="ghost small" data-open="waisentry">${esc(t("sec.open"))}</button>` : "";
    return `<button class="sec-band" style="--sec:${color}" aria-expanded="false" title="${esc(l.name)}">${SHIELD}
        <span class="sec-label">${esc(label)}</span>${l.controls.map((c) => `<span class="sec-chip" title="${esc(c.name)}">${esc(c.short)}</span>`).join("")}${CHEV}</button>
      <div class="sec-detail" style="--sec:${color}" hidden><p>${esc(l.summary)}</p>
        <dl>${l.controls.map((c) => `<dt>${esc(c.name)}</dt><dd>${esc(c.role)}</dd>`).join("")}</dl>
        <p class="muted">${esc(l.note)}</p>${open}</div>`;
  }).join("");
}

/* ---------------- color helpers ---------------- */
function mix(hex, pct, base = "#ffffff") {
  const p = (h) => [1, 3, 5].map((i) => parseInt(h.slice(i, i + 2), 16));
  const a = p(hex), b = p(base);
  return "#" + a.map((v, i) => Math.round(v * pct + b[i] * (1 - pct)).toString(16).padStart(2, "0")).join("");
}
const dark = () => matchMedia("(prefers-color-scheme: dark)").matches;

/* ---------------- hex geometry ---------------- */
function spiral(n) {
  const dirs = [[1, 0], [1, -1], [0, -1], [-1, 0], [-1, 1], [0, 1]];
  const out = [[0, 0]];
  for (let k = 1; out.length < n; k++) {
    let q = dirs[4][0] * k, r = dirs[4][1] * k;
    for (let i = 0; i < 6 && out.length < n; i++) {
      for (let j = 0; j < k && out.length < n; j++) { out.push([q, r]); q += dirs[i][0]; r += dirs[i][1]; }
    }
  }
  return out;
}
function hexPoints(cx, cy, r) {
  return [...Array(6)].map((_, i) => {
    const a = Math.PI / 180 * (60 * i - 30);
    return `${(cx + r * Math.cos(a)).toFixed(1)},${(cy + r * Math.sin(a)).toFixed(1)}`;
  }).join(" ");
}
/* ---------------- fitting text inside a pointy-top hexagon ---------------- */
const MEASURE = document.createElement("canvas").getContext("2d");
const FONT_STACK = 'Figtree, system-ui, -apple-system, "Segoe UI", sans-serif';
function textW(text, px, weight, spacingEm = 0) {
  MEASURE.font = `${weight} ${px}px ${FONT_STACK}`;
  return MEASURE.measureText(text).width + spacingEm * px * Math.max(text.length - 1, 0);
}
/* half-width of a pointy-top hexagon (circumradius rr) at vertical offset dy from its centre */
function hexHalfW(rr, dy) { const a = Math.abs(dy); return a <= rr / 2 ? rr * SQ3 / 2 : Math.max(0, (rr - a) * SQ3); }
/* usable width for a line whose glyphs span [top, bottom] (offsets from the centre), with side padding */
function room(rr, top, bottom, pad = 3.5) { return 2 * Math.min(hexHalfW(rr, top), hexHalfW(rr, bottom)) - 2 * pad; }
function ellipsize(text, px, weight, spacing, max) {
  if (textW(text, px, weight, spacing) <= max) return text;
  let t = text;
  while (t.length > 1 && textW(t + "…", px, weight, spacing) > max) t = t.slice(0, -1);
  return t.trimEnd() + "…";
}
/* shrink to fit (down to minPx), then ellipsize */
function fitLine(text, px, minPx, weight, spacing, max) {
  let p = px;
  while (p > minPx && textW(text, p, weight, spacing) > max) p = Math.round((p - 0.2) * 10) / 10;
  return { text: ellipsize(text, p, weight, spacing, max), px: p };
}
/* Up to two name lines, greedy by measured width; the second line sits lower, where the hexagon narrows. */
function fitName(name, rooms, px = 9.6, minPx = 7.8) {
  const words = name.trim().split(/\s+/);
  for (let p = px; p >= minPx - 1e-9; p = Math.round((p - 0.2) * 10) / 10) {
    const l1 = [];
    let i = 0;
    while (i < words.length && textW([...l1, words[i]].join(" "), p, 500) <= rooms[0]) l1.push(words[i++]);
    if (!l1.length) continue;                                    // first word too long at this size
    const rest = words.slice(i).join(" ");
    if (!rest) return { lines: [l1.join(" ")], px: p };
    if (textW(rest, p, 500) <= rooms[1]) return { lines: [l1.join(" "), rest], px: p };
  }
  const p = minPx, l1 = [];
  let i = 0;
  while (i < words.length && textW([...l1, words[i]].join(" "), p, 500) <= rooms[0]) l1.push(words[i++]);
  if (!l1.length) return { lines: [ellipsize(words[0], p, 500, 0, rooms[0])], px: p };
  const rest = words.slice(i).join(" ");
  return { lines: rest ? [l1.join(" "), ellipsize(rest, p, 500, 0, rooms[1])] : [l1.join(" ")], px: p };
}
function hexStyle(a, color) {
  const d = dark();
  const st = a.status;
  if (st === "demo_ready") return { fill: color, stroke: mix(color, 0.75, "#000000"), text: "#fff", sub: "rgba(255,255,255,.88)", dash: "" };
  if (st === "built") return { fill: d ? mix(color, 0.28, "#1b1c1a") : mix(color, 0.13), stroke: color, text: d ? mix(color, 0.6) : mix(color, 0.8, "#000000"), sub: d ? mix(color, 0.5) : mix(color, 0.85, "#000000"), dash: "" };
  if (st === "in_build") return { fill: d ? "#1b1c1a" : "#fbfaf7", stroke: color, text: d ? mix(color, 0.7) : mix(color, 0.85, "#000000"), sub: color, dash: "7 4" };
  return { fill: "transparent", stroke: color, text: d ? mix(color, 0.7) : mix(color, 0.85, "#000000"), sub: color, dash: "2.5 4" };
}
function hexSVG(a, color, cx, cy, r = R, opts = {}) {
  const s = hexStyle(a, color);
  const rr = r - 2;                                              // the drawn polygon's circumradius
  const hasInd = !!a.industry;
  // vertical layout (offsets from the centre): industry label, code, two name lines
  const L = hasInd ? { ind: -20.5, code: -0.5, n1: 12, n2: 21.2 } : { code: -3, n1: 10.5, n2: 19.7 };
  const label = a.short_name || a.name.split(" · ")[0];
  const name = fitName(label, [room(rr, L.n1 - 7.5, L.n1 + 2.4), room(rr, L.n2 - 7.5, L.n2 + 2.4)]);
  const lines = name.lines;
  let ind = "";
  if (hasInd) {
    const f = fitLine(a.industry_label || a.industry, 6.8, 5.4, 700, 0.1, room(rr, L.ind - 5.2, L.ind, 3));
    ind = `<text class="ind" x="${cx}" y="${cy + L.ind}" text-anchor="middle" fill="${s.sub}" style="font-size:${f.px}px">${esc(f.text)}</text>`;
  }
  const dot = a.status === "built" ? `<circle class="live" cx="${cx + r * 0.6}" cy="${cy - r * 0.68}" r="5.5" fill="var(--warn)" stroke="var(--surface)" stroke-width="1.5"/><text x="${cx + r * 0.6}" y="${cy - r * 0.68 + 3}" text-anchor="middle" font-size="8" font-weight="800" fill="#fff">!</text>` : "";
  return `<g class="hex" tabindex="0" role="button" data-id="${a.id}" aria-label="${esc(a.name)} — ${esc(S.cat.statuses[a.status].label)}">
    <polygon class="shape" points="${hexPoints(cx, cy, r - 2)}" fill="${s.fill}" stroke="${s.stroke}" stroke-width="2" stroke-dasharray="${s.dash}"/>
    ${ind}
    <text class="code" x="${cx}" y="${cy + L.code}" text-anchor="middle" fill="${s.text}">${esc(a.code)}</text>
    ${lines.map((l, i) => `<text class="nm" x="${cx}" y="${cy + (i ? L.n2 : L.n1)}" text-anchor="middle" fill="${s.sub}" style="font-size:${name.px}px">${esc(l)}</text>`).join("")}
    ${dot}</g>`;
}
function clusterSVG(agents, color) {
  const pos = spiral(agents.length).map(([q, r]) => [R * SQ3 * (q + r / 2), R * 1.5 * r]);
  const xs = pos.map((p) => p[0]), ys = pos.map((p) => p[1]);
  const minX = Math.min(...xs) - R * SQ3 / 2 - 6, maxX = Math.max(...xs) + R * SQ3 / 2 + 6;
  const minY = Math.min(...ys) - R - 6, maxY = Math.max(...ys) + R + 6;
  const w = maxX - minX, h = maxY - minY;
  // sort: demo-ready in the middle of the blob, library on the edge
  const ordered = [...agents].sort((a, b) => STATUS_ORDER.indexOf(a.status) - STATUS_ORDER.indexOf(b.status));
  const body = ordered.map((a, i) => hexSVG(a, color, pos[i][0] - minX, pos[i][1] - minY)).join("");
  return `<svg width="${w.toFixed(0)}" height="${h.toFixed(0)}" viewBox="0 0 ${w.toFixed(0)} ${h.toFixed(0)}">${body}</svg>`;
}
function miniHex(a, size = 40) {
  const color = S.realmOf.get(a.id).color;
  const s = hexStyle(a, color);
  const r = size / 2;
  return `<svg class="mini-hex" viewBox="0 0 ${size} ${size * 1.1}" style="width:${size}px;height:${size * 1.1}px"><polygon points="${hexPoints(r, r * 1.1, r - 2)}" fill="${s.fill}" stroke="${s.stroke}" stroke-width="2" stroke-dasharray="${s.dash}"/><text x="${r}" y="${r * 1.1 + 4.5}" text-anchor="middle" fill="${s.text}" font-size="${size * 0.32}">${esc(a.code)}</text></svg>`;
}

/* ---------------- filters ---------------- */
function matches(a) {
  const f = S.filters;
  if (f.status.size && !f.status.has(a.status)) return false;
  if (f.tier.size && !f.tier.has(a.model)) return false;
  if (f.q) {
    const hay = [a.name, a.code, a.tagline, a.description, a.persona, a.cluster, a.industry, ...(a.use_cases || []), ...(a.tools || []), a.realm].join(" ").toLowerCase();
    return f.q.toLowerCase().split(/\s+/).every((t) => hay.includes(t));
  }
  return true;
}
function applyFilters() {
  $$(".hex").forEach((g) => g.classList.toggle("dim", !matches(S.agents.get(g.dataset.id))));
  const any = S.filters.q || S.filters.status.size || S.filters.tier.size;
  $("#clear-filters").hidden = !any;
  if (S.view === "navigator") renderNavigator();
}
function renderFilterChips() {
  const c = S.cat.counts;
  $("#filter-status").innerHTML = STATUS_ORDER.map((k) => `<button class="chip" data-status="${k}" aria-pressed="false">${legendHex(k)}${esc(S.cat.statuses[k].label.split(" —")[0])} <span class="muted">${c.status[k] || 0}</span></button>`).join("");
  $("#filter-tier").innerHTML = Object.keys(S.cat.tiers).map((k) => `<button class="chip" data-tier="${k}" aria-pressed="false"><span class="tag ${k}" style="padding:0 5px">${TIER_LABEL[k]}</span><span class="muted">${c.tier[k] || 0}</span></button>`).join("");
  $$("#filter-status .chip").forEach((b) => b.onclick = () => toggleFilter("status", b.dataset.status, b));
  $$("#filter-tier .chip").forEach((b) => b.onclick = () => toggleFilter("tier", b.dataset.tier, b));
}
function toggleFilter(kind, val, btn) {
  const set = S.filters[kind];
  set.has(val) ? set.delete(val) : set.add(val);
  btn.setAttribute("aria-pressed", set.has(val));
  applyFilters();
}
function legendHex(status, color = "#2b78d0") {
  const s = hexStyle({ status }, color);
  return `<svg viewBox="0 0 20 22" width="14" height="15" style="stroke-linecap:butt"><polygon points="${hexPoints(10, 11, 8.5)}" fill="${s.fill}" stroke="${s.stroke}" stroke-width="1.6" stroke-dasharray="${status === "in_build" ? "3 2" : status === "library" ? "1.2 2" : ""}"/></svg>`;
}

/* ---------------- header + views ---------------- */
function renderHeader() {
  const c = S.cat.counts;
  $("#subtitle").textContent = S.cat.subtitle;
  const engines = S.cat.realms.filter((r) => r.agents.length).length;
  const stats = SHOWCASE()
    ? [[c.agents, t("stat.agents")], [c.realms, t("stat.segments")], [c.agents, t("stat.live")],
       [engines, t("stat.engines")], [c.tools, t("stat.tools")]]
    : [[c.agents, "agents"], [c.user_realms, "user realms + " + (c.realms - c.user_realms) + " internal"],
       [c.status.demo_ready || 0, "demo-ready"], [c.status.built || 0, "built, need demo"],
       [c.status.in_build || 0, "in build"], [c.status.library || 0, "library"],
       [engines, "Agent Engines"], [c.tools, "function tools"]];
  $("#stats").innerHTML = stats.map(([n, l]) => `<div class="stat"><b>${n}</b><span>${esc(l)}</span></div>`).join("");
  const tier = c.tier;
  const multi = Object.entries(c.pattern).filter(([k]) => k !== "single").reduce((s, [, v]) => s + v, 0);
  const term = TERM();
  $("#blocks-intro").innerHTML = [
    ["model", t("bi.models"), t("bi.models.p", { lite: tier.lite || 0, flash: tier.flash || 0, argon: tier.argon || 0 })],
    ["runtime", t("bi.runtime"), t("bi.runtime.p", { engines, term, multi })],
    ["tools", t("bi.tools"), t("bi.tools.p", { tools: c.tools })],
    ["grounding", t("bi.grounding"), t("bi.grounding.p", { term })],
  ].map(([k, h, p]) => `<div class="bi"><h3><span class="dot" style="background:${BLOCK_COLORS[k]}"></span>${h}</h3><p>${esc(p)}</p></div>`).join("");
  $("#legend").innerHTML = (SHOWCASE() ? "" : STATUS_ORDER.map((k) => `<span>${legendHex(k, "#5f5d57").replace('width="14" height="15"', 'width="20" height="22"')}${esc(S.cat.statuses[k].label)}</span>`).join(""))
    + S.cat.realms.map((r) => `<span><i style="width:12px;height:12px;border-radius:3px;background:${r.color};display:inline-block"></i>${esc(r.name)}${r.kind === "internal" ? " (internal)" : ""}</span>`).join("");
}

function renderHive() {
  const realm = (r) => {
    const n = r.agents.length, d = r.agents.filter((a) => a.status === "demo_ready").length;
    const clusters = r.clusters.map((c) => {
      const ag = r.agents.filter((a) => a.cluster === c.id);
      if (!ag.length) return "";
      return `<div class="cluster">${clusterSVG(ag, r.color)}<div class="cluster-label" title="${esc(c.blurb)}">${esc(c.name)}</div></div>`;
    }).join("");
    return `<section class="realm" data-realm="${r.id}" style="border-top:4px solid ${r.color}">
      <div class="realm-head"><h2 style="color:${r.color}">${esc(r.name)}</h2><span class="muted">${esc(t("realm.agents", { n }))}${SHOWCASE() ? "" : " · " + esc(t("realm.demo", { n: d }))}</span>${SHOWCASE() ? "" : `<span class="kind" style="color:${r.color}">${r.kind}</span>`}</div>
      <p class="realm-blurb">${esc(r.blurb)}</p>${securityBand(r.id)}<div class="clusters">${clusters}</div></section>`;
  };
  const by = Object.fromEntries(S.cat.realms.map((r) => [r.id, r]));
  const lay = (S.cat.layout && S.cat.layout.left) ? S.cat.layout : { left: ["platform", "government", "smb"], right: ["enterprise", "delivery"] };
  const placed = new Set([...lay.left, ...lay.right]);
  const left = lay.left.filter((k) => by[k]).map((k) => realm(by[k])).join("");
  const right = lay.right.filter((k) => by[k]).map((k) => realm(by[k])).join("");
  const extra = S.cat.realms.filter((r) => !placed.has(r.id)).map(realm).join("");
  $("#view-hive").innerHTML = `<div class="hive"><div class="hive-col">${left}${extra}</div><div class="hive-col">${right}</div></div>`;
  $$(".sec-band", $("#view-hive")).forEach((b) => b.onclick = () => {
    const open = b.getAttribute("aria-expanded") !== "true";
    b.setAttribute("aria-expanded", String(open));
    b.nextElementSibling.hidden = !open;
  });
  $$(".sec-detail [data-open]", $("#view-hive")).forEach((x) => x.onclick = () => openAgent(x.dataset.open));
  wireHexes($("#view-hive"));
  applyFilters();
}

function wireHexes(root) {
  let tip = $(".tip");
  if (!tip) { tip = document.createElement("div"); tip.className = "tip"; tip.hidden = true; document.body.appendChild(tip); }
  $$(".hex", root).forEach((g) => {
    const a = S.agents.get(g.dataset.id);
    g.addEventListener("click", () => openAgent(a.id));
    g.addEventListener("keydown", (e) => { if (e.key === "Enter" || e.key === " ") { e.preventDefault(); openAgent(a.id); } });
    g.addEventListener("mouseenter", () => {
      tip.innerHTML = `<b>${esc(a.name)}</b>${esc(a.tagline)}<div class="t-meta">${SHOWCASE() ? "" : esc(S.cat.statuses[a.status].label) + " · "}${TIER_LABEL[a.model]} · ${a.pattern}${a.aka ? " · " + esc(a.aka) : ""}</div>`;
      tip.hidden = false;
    });
    g.addEventListener("mousemove", (e) => {
      const x = Math.min(e.clientX + 14, innerWidth - 340);
      tip.style.left = x + "px"; tip.style.top = (e.clientY + 16) + "px";
    });
    g.addEventListener("mouseleave", () => { tip.hidden = true; });
  });
}

function agentCard(a) {
  const r = S.realmOf.get(a.id);
  const cl = r.clusters.find((c) => c.id === a.cluster);
  return `<article class="card">
    <div class="row">${miniHex(a)}<div><h3>${esc(a.name)}</h3><div class="muted small">${esc(r.name)} · ${esc(cl?.name || a.cluster)}</div></div></div>
    <div>${esc(a.tagline)}</div>
    <ul>${(a.use_cases || []).slice(0, 3).map((u) => `<li>${esc(u)}</li>`).join("")}</ul>
    <div class="foot"><span class="tag ${a.model}">${TIER_LABEL[a.model]}</span><span class="tag">${esc(a.pattern)}</span>${SHOWCASE() ? "" : `<span class="tag">${esc(S.cat.statuses[a.status].label.split(" —")[0])}</span>`}
    <button class="primary" style="margin-left:auto;padding:5px 14px" data-open="${a.id}">${esc(t("card.open"))}</button></div></article>`;
}
function renderNavigator() {
  const list = [...S.agents.values()].filter(matches);
  const groups = S.cat.realms.map((r) => {
    const ag = list.filter((a) => a.realm === r.id);
    if (!ag.length) return "";
    return `<h2 class="group-title" style="color:${r.color}">${esc(r.name)} <span class="muted">(${ag.length})</span></h2><div class="cards">${ag.map(agentCard).join("")}</div>`;
  }).join("");
  $("#view-navigator").innerHTML = (list.length ? `<p class="muted">${esc(t("nav.showing", { n: list.length, m: S.agents.size }))}</p>` : `<p class="muted">${esc(t("nav.none"))}</p>`) + groups;
  $$("[data-open]", $("#view-navigator")).forEach((b) => b.onclick = () => openAgent(b.dataset.open));
}
function chip(id) {
  const a = S.agents.get(id); if (!a) return "";
  const c = S.realmOf.get(id).color;
  return `<button class="agent-chip" data-open="${id}"><i style="background:${c}">${esc(a.code)}</i>${esc(a.name.split(" · ")[0])}</button>`;
}
function renderCompositions() {
  $("#view-compositions").innerHTML = `<p class="muted">${esc(t(SHOWCASE() ? "comp.intro" : "comp.intro.internal"))}</p>` + S.cat.compositions.map((c) => `
    <article class="comp"><div class="row" style="display:flex;gap:10px;align-items:baseline;flex-wrap:wrap"><h3>${esc(c.name)}</h3><span class="tag">${esc(c.kind)}</span><span class="tag">${esc(c.status)}</span></div>
    <p>${esc(c.summary)}</p>
    <div class="flow">${c.flow.map((s, i) => `${i ? '<span class="arrow">→</span>' : ""}<div class="step">${esc(s)}</div>`).join("")}</div>
    <div class="agent-chips">${c.agents.map(chip).join("")}</div>
    <div class="comp-blocks" style="margin-top:10px">${["models", "runtime", "tools", "grounding"].map((k) => `<div><b>${k}</b>${esc(c.blocks[k] || "")}</div>`).join("")}</div></article>`).join("");
  $$("[data-open]", $("#view-compositions")).forEach((b) => b.onclick = () => openAgent(b.dataset.open));
}
function renderSkills() {
  $("#view-skills").innerHTML = `<p class="muted">${esc(t("skills.intro"))}</p><div class="cards">` + S.cat.skills.map((s) => `
    <article class="card"><h3><code>${esc(s.id)}</code></h3><div>${esc(s.description)}</div>
    <div class="muted small">${esc(t("skills.tool"))}: <code>${esc(s.tool)}</code></div>
    <div class="agent-chips">${s.used_by.map(chip).join("") || `<span class="muted small">${esc(t("skills.unused"))}</span>`}</div></article>`).join("") + `</div>`;
  $$("[data-open]", $("#view-skills")).forEach((b) => b.onclick = () => openAgent(b.dataset.open));
}
function setView(v) {
  S.view = v;
  $$(".views button").forEach((b) => b.setAttribute("aria-selected", b.dataset.view === v));
  ["hive", "navigator", "compositions", "skills"].forEach((k) => $("#view-" + k).hidden = k !== v);
  $("#blocks-intro").hidden = v !== "hive";
  if (v === "navigator") renderNavigator();
  if (v === "compositions") renderCompositions();
  if (v === "skills") renderSkills();
  history.replaceState(null, "", v === "hive" ? location.pathname + (S.open ? "#" + S.open : "") : "#view=" + v);
}

/* ---------------- agent panel ---------------- */
function stepName(a, author) {
  if (!author) return a.name;
  if (author === a.adk_name) return a.name;
  if (author.endsWith("_concierge")) { const term = TERM(); return t("step.concierge", { term, Term: term[0].toUpperCase() + term.slice(1) }); }
  if (author.endsWith("__loader")) return t("step.loader");
  const m = author.match(/__(\w+?)$/);
  if (m) {
    if (m[1] === "final" || m[1] === "synthesis") return a.name + " · " + (m[1] === "final" ? "final" : "synthesis");
    const st = (a.steps || []).find((s) => s.id === m[1]);
    if (st) return st.name;
  }
  return author;
}

function renderBlocks(a) {
  const b = a.blocks;
  const tools = b.tools.map((t) => `<div class="item" data-tool="${esc(t.name)}"><div><code>${esc(t.name)}</code>${t.kind !== "function" ? ` <span class="kind">${esc(t.kind)}</span>` : ""}${t.step ? ` <span class="kind">${esc(t.step)}</span>` : ""}<div class="desc">${esc(t.summary)}</div></div><span class="cnt"></span></div>`).join("") || `<p class="muted">${esc(t("blk.notools"))}</p>`;
  const groundKey = (g) => g.kind;
  const grounding = b.grounding.map((g) => `<div class="item" data-ground="${groundKey(g)}"><div><b>${esc(g.label)}</b>${g.step ? ` <span class="kind">${esc(g.step)}</span>` : ""}<div class="desc">${esc(g.detail)}</div></div><span class="cnt"></span></div>`).join("") || `<p class="muted">${esc(t("blk.noground"))}</p>`;
  const steps = b.runtime.steps.length ? `<div class="steps">${b.runtime.steps.map((s) => `<div class="item" data-step="${esc(s.id)}"><div><b>${esc(s.name)}</b> <span class="tag ${s.model}">${TIER_LABEL[s.model]}</span>${s.agent_ref ? ` <span class="kind">AgentTool</span>` : ""}<div class="desc">${esc(s.role)}</div></div><span class="cnt"></span></div>`).join("")}</div>` : "";
  const patternDesc = t("pat." + b.runtime.pattern);
  $("#p-blocks").innerHTML = `
    <div class="blk" id="blk-model"><h3><span class="sw" style="background:${BLOCK_COLORS.model}"></span>${esc(t("blk.model"))}<span class="n" id="tok"></span></h3>
      <p><span class="tag ${b.model.tier}">${esc(b.model.label)}</span> <code>${esc(b.model.model_id)}</code></p>
      <p class="muted">${esc(b.model.why)}</p>
      ${b.model.also_uses.length ? `<p class="small">${esc(t("blk.also"))} ${b.model.also_uses.map(esc).join(", ")}</p>` : ""}
      <p class="small muted">${esc(t("blk.policy"))} ${esc(b.model.policy)}</p></div>
    <div class="blk" id="blk-runtime"><h3><span class="sw" style="background:${BLOCK_COLORS.runtime}"></span>${esc(t("blk.runtime"))}<span class="n" id="rt-n"></span></h3>
      <dl class="kv"><dt>${esc(t("blk.platform"))}</dt><dd>${esc(b.runtime.label)}</dd><dt>${esc(t("blk.engine"))}</dt><dd id="rt-engine">${esc(b.runtime.engine)}</dd>
      <dt>${esc(t("blk.region"))}</dt><dd>${esc(b.runtime.region)}</dd><dt>${esc(t("blk.pattern"))}</dt><dd>${esc(patternDesc)}</dd><dt>${esc(t("blk.sessions"))}</dt><dd id="rt-session">${esc(b.runtime.sessions)}</dd></dl>${steps}</div>
    <div class="blk" id="blk-tools"><h3><span class="sw" style="background:${BLOCK_COLORS.tools}"></span>${esc(t("blk.tools"))}<span class="n">${b.tools.length}</span></h3>${tools}</div>
    <div class="blk" id="blk-grounding"><h3><span class="sw" style="background:${BLOCK_COLORS.grounding}"></span>${esc(t("blk.grounding"))}<span class="n">${b.grounding.length}</span></h3>${grounding}<div class="sources small" id="sources"></div></div>
    ${layersFor(a.realm).filter((l) => l.id === "google_security").map((l) => `<div class="blk blk-sec" style="--sec:${LAYER_COLORS[l.id]}"><h3>${SHIELD}${esc(l.name)}<span class="n">${esc(t("sec.reference"))}</span></h3>
      ${l.controls.map((c) => `<div class="item"><div><b>${esc(c.name)}</b><div class="desc">${esc(c.brief || firstSentence(c.role))}</div></div></div>`).join("")}
      <p class="small muted">${esc(l.note)}</p></div>`).join("")}
    ${a.kpis?.length ? `<div class="blk"><h3>${esc(t("blk.kpis"))}</h3><ul class="small" style="margin:0;padding-left:18px">${a.kpis.map((k) => `<li>${esc(k)}</li>`).join("")}</ul></div>` : ""}
    ${a.related?.length ? `<div class="blk"><h3>${esc(t("blk.related"))}</h3><div class="agent-chips">${a.related.map(chip).join("")}</div></div>` : ""}`;
  $$("[data-open]", $("#p-blocks")).forEach((x) => x.onclick = () => openAgent(x.dataset.open));
}

function pulse(sel, blockId) {
  const el = $(sel, $("#p-blocks"));
  const blk = $("#" + blockId);
  if (blk) { blk.classList.add("active"); clearTimeout(blk._t); blk._t = setTimeout(() => blk.classList.remove("active"), 1600); }
  if (!el) return;
  el.classList.add("hit");
  const c = $(".cnt", el); c.textContent = "×" + ((+c.textContent.slice(1) || 0) + 1);
  clearTimeout(el._t); el._t = setTimeout(() => el.classList.remove("hit"), 2200);
}

function openAgent(id) {
  const a = S.agents.get(id); if (!a) return;
  if (S.open && S.open !== id) { const prev = S.open; saveChat(); maybeFeedback(prev); }
  const r = S.realmOf.get(id);
  const cl = r.clusters.find((c) => c.id === a.cluster);
  S.open = id; S.files = []; renderFiles();
  $("#p-hex").innerHTML = miniHex(a, 54);
  $("#p-name").textContent = a.name;
  $("#p-tagline").textContent = a.tagline;
  $("#p-meta").innerHTML = `<span class="tag" style="color:${r.color}">${esc(r.name)}</span><span class="tag">${esc(cl?.name || a.cluster)}</span>${SHOWCASE() ? "" : `<span class="tag">${legendHex(a.status, r.color)} ${esc(S.cat.statuses[a.status].label)}</span>`}${a.aka ? `<span class="tag">${esc(a.aka)}</span>` : ""}<span class="tag ${a.model}">${TIER_LABEL[a.model]}</span>`;
  $("#p-about").innerHTML = `<summary>${esc(t("about", { persona: a.persona }))}</summary><p>${esc(a.description)}</p><b class="small">${esc(t("about.uses"))}</b><ul>${a.use_cases.map((u) => `<li>${esc(u)}</li>`).join("")}</ul><b class="small">${esc(t("about.output"))}</b><p>${esc(a.output)}</p>`;
  $("#samples").innerHTML = a.samples.map((s) => `<button class="sample" type="button">${esc(s)}</button>`).join("");
  $$("#samples .sample").forEach((b, i) => b.onclick = () => { $("#msg").value = a.samples[i]; S.sample = true; send(); });
  $("#doc-btn").hidden = !a.sample_doc;
  renderBlocks(a);
  const sess = S.sessions.get(id);
  $("#chat").innerHTML = sess?.html || `<div class="empty-chat">${t("chat.empty")}</div>`;
  $("#runtime-line").textContent = sess?.line || "";
  $("#panel").hidden = false; $("#scrim").hidden = false;
  document.body.style.overflow = "hidden";
  history.replaceState(null, "", "#" + id);
  setTimeout(() => $("#msg").focus(), 50);
  warm(a.realm);
}
function closeAgent() {
  saveChat();
  const prev = S.open;
  S.open = null;
  $("#panel").hidden = true; $("#scrim").hidden = true;
  document.body.style.overflow = "";
  history.replaceState(null, "", S.view === "hive" ? location.pathname : "#view=" + S.view);
  if (prev) maybeFeedback(prev);
}
function saveChat() {
  if (!S.open) return;
  const s = S.sessions.get(S.open);
  if (s) { s.html = $("#chat").innerHTML; s.line = $("#runtime-line").textContent; }
}

async function warm(realm) {
  if (S.warm.has(realm)) return;
  S.warm.set(realm, "warming");
  const line = $("#runtime-line");
  if (!line.textContent) line.textContent = t("rt.waking", { term: TERM() });
  try {
    const r = await fetch(`/api/warm/${realm}`, { method: "POST" });
    const j = await r.json();
    S.warm.set(realm, r.ok ? "ready" : "error");
    if (S.open && S.agents.get(S.open).realm === realm && line.textContent === t("rt.waking", { term: TERM() })) {
      line.textContent = r.ok ? t("rt.ready", { s: j.seconds }) : t("rt.engine", { x: j.detail || "unavailable" });
    }
  } catch { S.warm.delete(realm); }
}

/* ---------------- running a turn ---------------- */
async function ensureSession(a) {
  let s = S.sessions.get(a.id);
  if (s?.id) return s;
  const r = await fetch("/api/session", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ agent_id: a.id }) });
  const j = await r.json();
  if (!r.ok) throw new Error(j.detail || "could not create session");
  s = { id: j.session_id, engine: j.engine, html: "", line: "" };
  S.sessions.set(a.id, s);
  $("#rt-engine").textContent = `${a.blocks.runtime.engine} · ${j.engine}`;
  $("#rt-session").textContent = t("sess.managed", { id: j.session_id.slice(0, 12) });
  return s;
}

function md(text) {
  const html = DOMPurify.sanitize(marked.parse(text || "", { gfm: true, breaks: false }));
  const div = document.createElement("div");
  div.innerHTML = html;
  $$("pre code", div).forEach((code) => {
    const lang = (code.className.match(/language-(\w+)/) || [])[1];
    if (lang === "mermaid") {
      const box = document.createElement("div");
      box.className = "mermaid-box"; box.dataset.src = code.textContent;
      code.parentElement.replaceWith(box);
    } else if (lang === "html") {
      const btn = document.createElement("button");
      btn.className = "ghost small preview-btn"; btn.type = "button"; btn.textContent = t("prev.btn"); btn.dataset.preview = "1";
      code.parentElement.appendChild(btn);
    }
  });
  $$("a", div).forEach((x) => { x.target = "_blank"; x.rel = "noopener noreferrer"; });
  return div.innerHTML;
}
let mermaidN = 0;
async function renderMermaid(root) {
  for (const box of $$(".mermaid-box:not([data-done])", root)) {
    box.dataset.done = "1";
    try {
      const { svg } = await mermaid.render("mmd" + (++mermaidN), box.dataset.src);
      box.innerHTML = svg;
    } catch { box.innerHTML = `<pre>${esc(box.dataset.src)}</pre>`; }
  }
}

function addUser(text, files) {
  const chat = $("#chat");
  $(".empty-chat", chat)?.remove();
  const d = document.createElement("div");
  d.className = "msg user";
  d.innerHTML = esc(text.length > 1600 ? text.slice(0, 1600) + "…" : text) + (files.length ? `<div class="att">📎 ${files.map((f) => esc(f.name)).join(", ")}</div>` : "");
  chat.appendChild(d);
}

function turnContainer() {
  const chat = $("#chat");
  const work = document.createElement("details");
  work.className = "work"; work.open = true;
  work.innerHTML = `<summary>${esc(t("work.title"))} <span class="muted" data-sum></span></summary><div class="work-list"></div><div class="typing"><i></i><i></i><i></i></div>`;
  chat.appendChild(work);
  return work;
}

function addEv(work, cls, html) {
  const d = document.createElement("div");
  d.className = "ev " + cls;
  d.innerHTML = `<span class="k"></span><div>${html}</div>`;
  $(".work-list", work).appendChild(d);
  const chat = $("#chat"); chat.scrollTop = chat.scrollHeight;
}

function groundingKindForCall(name) {
  if (/google_search/.test(name)) return "google_search";
  if (/discovery_engine_search|vertex_ai_search/.test(name)) return "kb";
  if (/execute_sql|get_table_info|list_table_ids/.test(name)) return "bigquery";
  return null;
}

async function send() {
  if (S.running) return;
  const a = S.agents.get(S.open);
  const text = $("#msg").value.trim();
  if (!text) return;
  const files = S.files.slice();
  const sample = S.sample; S.sample = false;
  S.running = true; $("#send").disabled = true;
  $("#msg").value = ""; S.files = []; renderFiles();
  addUser(text, files);
  const work = turnContainer();
  const line = $("#runtime-line");
  const tokens = { prompt: 0, output: 0, thoughts: 0 };
  let lastAuthor = null, nEvents = 0, gotText = false;
  try {
    line.textContent = t("rt.session");
    const sess = await ensureSession(a);
    line.textContent = t("rt.running");
    const resp = await fetch("/api/run", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ agent_id: a.id, session_id: sess.id, message: text, files, lang: LANG, sample }),
    });
    if (!resp.ok) { const j = await resp.json().catch(() => ({})); throw new Error(j.detail || resp.statusText); }
    const reader = resp.body.getReader();
    const dec = new TextDecoder();
    let buf = "";
    for (;;) {
      const { value, done } = await reader.read();
      if (done) break;
      buf += dec.decode(value, { stream: true });
      let i;
      while ((i = buf.indexOf("\n\n")) >= 0) {
        const chunk = buf.slice(0, i); buf = buf.slice(i + 2);
        const dataLine = chunk.split("\n").find((l) => l.startsWith("data: "));
        if (!dataLine) continue;
        const ev = JSON.parse(dataLine.slice(6));
        nEvents++;
        if (ev.author && ev.author !== lastAuthor && ["call", "text", "result", "grounding"].includes(ev.type)) {
          lastAuthor = ev.author;
          const nm = stepName(a, ev.author);
          addEv(work, "agent", `<b>${esc(nm)}</b> <span class="muted">${esc(t("work.working"))}</span>`);
          const m = ev.author.match(/__(\w+?)$/);
          if (m) pulse(`[data-step="${m[1]}"]`, "blk-runtime"); else pulse("#none", "blk-runtime");
        }
        handleEvent(a, work, ev, tokens, () => { gotText = true; });
      }
    }
    if (!gotText) addEv(work, "error", esc(t("work.notext")));
    else S.ran.add(a.id);
  } catch (e) {
    addEv(work, "error", `<b>${esc(t("work.error"))}</b> ${esc(e.message)}`);
    if (String(e.message).includes("session")) S.sessions.delete(a.id);
  } finally {
    $(".typing", work)?.remove();
    $("[data-sum]", work).textContent = t("work.steps", { n: $$(".ev", work).length });
    if ($$(".ev.call", work).length === 0 && $$(".ev.error", work).length === 0) work.open = false;
    S.running = false; $("#send").disabled = false;
    const sess = S.sessions.get(a.id); if (sess) { sess.html = $("#chat").innerHTML; sess.line = line.textContent; }
    $("#msg").focus();
  }

  function handleEvent(a, work, ev, tokens, onText) {
    const chat = $("#chat");
    switch (ev.type) {
      case "runtime":
        line.textContent = t("rt.first", { s: ev.first_event_s }); break;
      case "call": {
        const args = JSON.stringify(ev.args || {});
        addEv(work, "call", `<details><summary><code>${esc(ev.name)}</code> <span class="muted">${esc(args.length > 90 ? args.slice(0, 90) + "…" : args)}</span></summary><pre>${esc(JSON.stringify(ev.args, null, 2))}</pre></details>`);
        pulse(`[data-tool="${CSS.escape(ev.name)}"]`, "blk-tools");
        const gk = groundingKindForCall(ev.name);
        if (gk) pulse(`[data-ground="${gk}"]`, "blk-grounding");
        const st = (a.steps || []).find((s) => ev.name === `${a.id}__${s.id}`);
        if (st) pulse(`[data-step="${st.id}"]`, "blk-runtime");
        break;
      }
      case "result": {
        let pretty = ev.response;
        try { pretty = JSON.stringify(JSON.parse(ev.response), null, 2); } catch {}
        const status = (ev.response.match(/"status":\s*"(\w+)"/) || [])[1];
        addEv(work, "result", `<details><summary><code>${esc(ev.name)}</code> ${esc(t("work.returned"))} ${status ? `<b>${esc(status)}</b>` : ""}${/simulated":\s*true/.test(ev.response) ? ` <span class="kind">${esc(t("work.simulated"))}</span>` : ""}</summary><pre>${esc(pretty)}${ev.truncated ? "\n…" : ""}</pre></details>`);
        break;
      }
      case "grounding": {
        pulse(`[data-ground="${ev.kind}"]`, "blk-grounding");
        const src = ev.sources.map((s) => s.uri ? `<a href="${esc(s.uri)}" target="_blank" rel="noopener noreferrer">${esc(s.title || s.uri)}</a>` : esc(s.title)).join(" · ");
        addEv(work, "grounding", `<b>${esc(ev.kind === "kb" ? t("work.kb") : t("work.gs"))}</b> ${ev.queries?.length ? `<span class="muted">“${esc(ev.queries.join("”, “"))}”</span>` : ""}<div class="sources">${src}</div>`);
        if (src) $("#sources").innerHTML = `<b>${esc(t("work.sources"))}</b> ${src}`;
        break;
      }
      case "usage":
        tokens.prompt += ev.prompt; tokens.output += ev.output; tokens.thoughts += ev.thoughts || 0;
        $("#tok").textContent = t("tok.turn", { n: (tokens.prompt + tokens.output + tokens.thoughts).toLocaleString() });
        pulse("#none", "blk-model");
        break;
      case "thought":
        addEv(work, "usage", `<details><summary class="muted">${esc(t("work.thinking"))}</summary><pre>${esc(ev.text)}</pre></details>`); break;
      case "text": {
        onText();
        const d = document.createElement("div");
        d.className = "msg agent";
        d.innerHTML = `<div class="who">${esc(stepName(a, ev.author))}</div>` + md(ev.text);
        chat.insertBefore(d, null);
        renderMermaid(d);
        $$("[data-preview]", d).forEach((b) => b.onclick = () => openPreview(b.parentElement.querySelector("code").textContent));
        chat.scrollTop = chat.scrollHeight;
        break;
      }
      case "file": {
        if ($(`[data-file="${CSS.escape(ev.id)}"]`, chat)) break;   // the same file can arrive via a step and its parent
        const bytes = Uint8Array.from(atob(ev.b64), (c) => c.charCodeAt(0));
        const url = URL.createObjectURL(new Blob([bytes], { type: ev.mime }));
        const ext = (ev.name.split(".").pop() || "").toUpperCase();
        const d = document.createElement("div");
        d.className = "msg agent file-card";
        d.dataset.file = ev.id;
        d.innerHTML = `<span class="file-ext">${esc(ext)}</span><div><b>${esc(ev.name)}</b><div class="muted small">${(ev.size / 1024).toFixed(1)} KB · ${esc(t("file.by", { who: stepName(a, ev.author) }))}</div></div><a class="primary" href="${url}" download="${esc(ev.name)}">${esc(t("file.download"))}</a>`;
        chat.insertBefore(d, null);
        addEv(work, "result", `<b>${esc(t("work.deliverable"))}</b> <code>${esc(ev.name)}</code> <span class="muted">${esc(t("work.saved"))}</span>`);
        chat.scrollTop = chat.scrollHeight;
        break;
      }
      case "state":
        if (ev.keys.includes("client_material")) addEv(work, "grounding", `<b>${esc(t("step.loader"))}</b> <span class="muted">${esc(t("work.loader"))}</span>`);
        break;
      case "error":
        addEv(work, "error", `<b>${esc(t("work.error"))}</b> ${esc(ev.message)}`); break;
      case "budget":
        S.budget = ev; break;
      case "done": {
        const n = Math.max(ev.tokens || 0, tokens.prompt + tokens.output + tokens.thoughts);
        line.textContent = t("rt.done", { s: ev.seconds, tok: n.toLocaleString() })
          + (S.budget && S.budget.limit ? " · " + t("rt.budget", { used: (S.budget.session_tokens || 0).toLocaleString(), limit: S.budget.limit.toLocaleString() }) : "");
        S.budget = null;
        break;
      }
    }
  }
}

function openPreview(html) {
  $("#preview-frame").srcdoc = html;
  $("#preview").hidden = false;
}

function renderFiles() {
  $("#files").innerHTML = S.files.map((f, i) => `<span class="tag">📎 ${esc(f.name)} <button class="icon" style="width:18px;height:18px" data-rm="${i}" aria-label="Remove">×</button></span>`).join("");
  $$("[data-rm]").forEach((b) => b.onclick = () => { S.files.splice(+b.dataset.rm, 1); renderFiles(); });
}

/* ---------------- init ---------------- */
function useCatalog() {
  S.cat = localize(S.raw, LANG);
  S.agents.clear(); S.realmOf.clear();
  for (const r of S.cat.realms) for (const a of r.agents) { S.agents.set(a.id, a); S.realmOf.set(a.id, r); }
  $("#title").textContent = S.cat.title;
  document.title = S.cat.title;
  applyStatic();
  $("#filter-status").hidden = SHOWCASE();
  renderHeader(); renderFilterChips(); renderHive();
  if (S.view !== "hive") setView(S.view);
}

function renderUser() {
  const box = $("#user");
  if (!box) return;
  const langs = SHOWCASE() ? `<div class="lang" role="group" aria-label="${esc(t("lang"))}">${["en", "es"].map((l) => `<button data-lang="${l}" aria-pressed="${l === LANG}">${l.toUpperCase()}</button>`).join("")}</div>` : "";
  const me = S.me ? `<span class="me" title="${esc(S.me.email)}">${S.me.picture ? `<img src="${esc(S.me.picture)}" alt="" referrerpolicy="no-referrer">` : ""}<span>${esc(S.me.name || S.me.email)}</span></span>`
    + (S.me.admin ? `<a class="ghost small" href="/admin">${esc(t("user.admin"))}</a>` : "")
    + `<button class="ghost small" id="signout">${esc(t("user.signout"))}</button>` : "";
  box.innerHTML = langs + me;
  $$("[data-lang]", box).forEach((b) => b.onclick = () => {
    setLang(b.dataset.lang);
    const open = S.open; if (open) saveChat();
    useCatalog(); renderUser();
    if (open) openAgent(open);
  });
  const so = $("#signout", box);
  if (so) so.onclick = async () => { await fetch("/api/auth/logout", { method: "POST" }); location.reload(); };
}

async function authGate() {
  const r = await fetch("/api/auth/config");
  if (!r.ok) return true;                         // internal edition: IAP in front, no app sign-in
  S.auth = await r.json();
  const me = await fetch("/api/me");
  if (me.ok) { S.me = await me.json(); return true; }
  showLogin();
  return false;
}

function showLogin() {
  setLang(LANG);
  const box = $("#login");
  box.hidden = false;
  applyStatic(box);
  $$("[data-lang]", box).forEach((b) => {
    b.setAttribute("aria-pressed", b.dataset.lang === LANG);
    b.onclick = () => { setLang(b.dataset.lang); showLogin(); };
  });
  const render = () => {
    google.accounts.id.initialize({ client_id: S.auth.client_id, callback: onCredential, ux_mode: "popup", auto_select: false, context: "signin" });
    $("#gsi").innerHTML = "";
    google.accounts.id.renderButton($("#gsi"), { theme: "outline", size: "large", shape: "pill", text: "signin_with", locale: LANG, width: 280 });
  };
  if (window.google?.accounts?.id) render();
  else {
    const sc = document.createElement("script");
    sc.src = "https://accounts.google.com/gsi/client"; sc.async = true; sc.onload = render;
    document.head.appendChild(sc);
  }
}

async function onCredential(resp) {
  $("#login-status").textContent = t("login.busy");
  const r = await fetch("/api/auth/google", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ credential: resp.credential, lang: LANG }) });
  if (!r.ok) { const j = await r.json().catch(() => ({})); $("#login-status").textContent = t("login.failed", { e: j.detail || r.statusText }); return; }
  location.reload();
}

/* ---------------- feedback ---------------- */
const FACES = [
  ["#d64545", "M8 16.5c1.2-1.6 2.5-2.3 4-2.3s2.8.7 4 2.3"],
  ["#e8833a", "M8.5 16c1-1 2.2-1.4 3.5-1.4s2.5.4 3.5 1.4"],
  ["#e3b21c", "M8.5 15.5h7"],
  ["#7cb342", "M8.5 14.5c1 1.1 2.2 1.6 3.5 1.6s2.5-.5 3.5-1.6"],
  ["#2e9e5b", "M7.8 13.8c1.1 1.9 2.5 2.8 4.2 2.8s3.1-.9 4.2-2.8"],
];
function faceSVG(i) {
  const [c, mouth] = FACES[i];
  return `<svg viewBox="0 0 24 24" aria-hidden="true" style="color:${c}"><circle cx="12" cy="12" r="10" fill="${c}" fill-opacity=".14" stroke="currentColor"/><circle cx="9" cy="10" r="1.1" fill="currentColor" stroke="none"/><circle cx="15" cy="10" r="1.1" fill="currentColor" stroke="none"/><path d="${mouth}" stroke="currentColor" fill="none"/></svg>`;
}
function maybeFeedback(agentId) {
  if (!SHOWCASE() || !S.me || !S.ran.has(agentId) || S.rated.has(agentId)) return;
  S.rated.add(agentId);
  const a = S.agents.get(agentId);
  const box = $("#feedback");
  let rating = 0;
  box.innerHTML = `<div class="modal-box fb-box" role="dialog" aria-modal="true" aria-labelledby="fb-title">
    <h3 id="fb-title">${esc(t("fb.title"))}</h3><p class="muted">${esc(a.name)}</p>
    <div class="faces">${[1, 2, 3, 4, 5].map((n) => `<button type="button" class="face" data-n="${n}" aria-label="${n} — ${esc(t("fb." + n))}">${faceSVG(n - 1)}<span>${esc(t("fb." + n))}</span></button>`).join("")}</div>
    <textarea id="fb-comment" rows="2" maxlength="1000" placeholder="${esc(t("fb.comment"))}"></textarea>
    <div class="fb-actions"><button type="button" class="ghost" id="fb-skip">${esc(t("fb.skip"))}</button><button type="button" class="primary" id="fb-send" disabled>${esc(t("fb.send"))}</button></div></div>`;
  box.hidden = false;
  $$(".face", box).forEach((b) => b.onclick = () => {
    rating = +b.dataset.n;
    $$(".face", box).forEach((x) => x.setAttribute("aria-pressed", x === b));
    $("#fb-send").disabled = false;
  });
  const close = () => { box.hidden = true; box.innerHTML = ""; };
  $("#fb-skip").onclick = close;
  $("#fb-send").onclick = async () => {
    const sess = S.sessions.get(agentId);
    await fetch("/api/feedback", { method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ agent_id: agentId, rating, comment: $("#fb-comment").value.trim(), session_id: sess?.id || "", lang: LANG }) }).catch(() => {});
    box.querySelector(".fb-box").innerHTML = `<h3>${esc(t("fb.thanks"))}</h3>`;
    setTimeout(close, 1200);
  };
}

async function init() {
  mermaid.initialize({ startOnLoad: false, theme: "neutral", securityLevel: "strict" });
  if (!(await authGate())) return;
  S.raw = await (await fetch("/api/catalog")).json();
  if (S.raw.edition && S.raw.edition !== "internal") setLang(LANG); else LANG = "en";
  useCatalog();
  renderUser();
  if (document.fonts && document.fonts.status !== "loaded") document.fonts.ready.then(() => renderHive());

  $$(".views button").forEach((b) => b.onclick = () => setView(b.dataset.view));
  $("#q").addEventListener("input", (e) => { S.filters.q = e.target.value.trim(); applyFilters(); });
  $("#clear-filters").onclick = () => {
    S.filters.q = ""; S.filters.status.clear(); S.filters.tier.clear(); $("#q").value = "";
    $$(".chip[aria-pressed]").forEach((c) => c.setAttribute("aria-pressed", "false")); applyFilters();
  };
  $("#p-close").onclick = closeAgent; $("#scrim").onclick = closeAgent;
  $("#preview-close").onclick = () => { $("#preview").hidden = true; $("#preview-frame").srcdoc = ""; };
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") { if (!$("#feedback").hidden) $("#fb-skip")?.click(); else if (!$("#preview").hidden) $("#preview-close").click(); else if (S.open) closeAgent(); }
  });
  $("#composer").addEventListener("submit", (e) => { e.preventDefault(); send(); });
  $("#msg").addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } });
  $("#new-session").onclick = () => {
    if (!S.open) return;
    S.sessions.delete(S.open);
    $("#chat").innerHTML = `<div class="empty-chat">${esc(t("chat.new"))}</div>`;
    $("#runtime-line").textContent = "";
  };
  $("#doc-btn").onclick = async () => {
    const a = S.agents.get(S.open);
    const r = await fetch(`/api/doc/${a.sample_doc}`);
    if (!r.ok) return;
    const j = await r.json();
    $("#msg").value = ($("#msg").value ? $("#msg").value + "\n\n" : t("msg.docintro", { t: j.title }) + "\n\n") + j.text;
    $("#msg").focus();
  };
  $("#file").addEventListener("change", async (e) => {
    for (const f of e.target.files) {
      if (f.size > 7 * 1024 * 1024) { alert(t("msg.toobig", { f: f.name })); continue; }
      const data = await new Promise((res) => { const fr = new FileReader(); fr.onload = () => res(fr.result.split(",")[1]); fr.readAsDataURL(f); });
      S.files.push({ name: f.name, mime_type: f.type || "application/octet-stream", data });
    }
    e.target.value = ""; renderFiles();
  });
  matchMedia("(prefers-color-scheme: dark)").addEventListener("change", () => renderHive());

  const h = location.hash.slice(1);
  if (h.startsWith("view=")) setView(h.slice(5));
  else if (h && S.agents.has(h)) openAgent(h);
}
init().catch((e) => { document.body.insertAdjacentHTML("afterbegin", `<p style="padding:20px;color:var(--danger)">${esc(t("load.fail", { e: e.message }))}</p>`); });
