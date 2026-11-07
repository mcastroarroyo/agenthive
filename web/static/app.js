/* Wursta Agent Hive — vanilla JS UI. Catalog from /api/catalog; live runs stream from /api/run (SSE). */
"use strict";

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const SQ3 = Math.sqrt(3);
const R = 42; // hex radius in px

const S = {
  cat: null, agents: new Map(), realmOf: new Map(), view: "hive",
  filters: { q: "", status: new Set(), tier: new Set() },
  open: null, sessions: new Map(), running: false, files: [], warm: new Map(),
};

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
    const label = l.id === "waisentry" ? "Protected by WAISentry" : "Security layer";
    const open = l.id === "waisentry" && S.agents.has("waisentry")
      ? `<button class="ghost small" data-open="waisentry">Open the WAISentry SOC demo</button>` : "";
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
function wrapName(name, max = 12) {
  const words = name.replace(/·.*$/, "").trim().split(/\s+/);
  const lines = [""];
  for (const w of words) {
    const cur = lines[lines.length - 1];
    if ((cur + " " + w).trim().length > max && cur) { if (lines.length === 2) { lines[1] += "…"; break; } lines.push(w); }
    else lines[lines.length - 1] = (cur + " " + w).trim();
  }
  return lines;
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
  const lines = wrapName(a.name.split(" · ")[0]);
  const ind = a.industry ? `<text class="ind" x="${cx}" y="${cy - r * 0.6}" text-anchor="middle" fill="${s.sub}">${esc(a.industry)}</text>` : "";
  const dot = a.status === "built" ? `<circle class="live" cx="${cx + r * 0.6}" cy="${cy - r * 0.68}" r="5.5" fill="var(--warn)" stroke="var(--surface)" stroke-width="1.5"/><text x="${cx + r * 0.6}" y="${cy - r * 0.68 + 3}" text-anchor="middle" font-size="8" font-weight="800" fill="#fff">!</text>` : "";
  return `<g class="hex" tabindex="0" role="button" data-id="${a.id}" aria-label="${esc(a.name)} — ${esc(S.cat.statuses[a.status].label)}">
    <polygon class="shape" points="${hexPoints(cx, cy, r - 2)}" fill="${s.fill}" stroke="${s.stroke}" stroke-width="2" stroke-dasharray="${s.dash}"/>
    ${ind}
    <text class="code" x="${cx}" y="${cy + (a.industry ? 1 : -2)}" text-anchor="middle" fill="${s.text}">${esc(a.code)}</text>
    ${lines.map((l, i) => `<text class="nm" x="${cx}" y="${cy + 14 + i * 10.5 + (a.industry ? 2 : 0)}" text-anchor="middle" fill="${s.sub}">${esc(l)}</text>`).join("")}
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
  $("#stats").innerHTML = [
    [c.agents, "agents"], [c.user_realms, "user realms + " + (c.realms - c.user_realms) + " internal"],
    [c.status.demo_ready || 0, "demo-ready"], [c.status.built || 0, "built, need demo"],
    [c.status.in_build || 0, "in build"], [c.status.library || 0, "library"],
    [engines, "Agent Engines"], [c.tools, "function tools"],
  ].map(([n, l]) => `<div class="stat"><b>${n}</b><span>${esc(l)}</span></div>`).join("");
  const t = c.tier;
  const multi = Object.entries(c.pattern).filter(([k]) => k !== "single").reduce((s, [, v]) => s + v, 0);
  $("#blocks-intro").innerHTML = [
    ["model", "Models", `Gemini tiers by cost: Flash-Lite ${t.lite || 0} · Flash ${t.flash || 0} · Argon ${t.argon || 0} (only where deep reasoning is the product).`],
    ["runtime", "Runtime", `${engines} Vertex AI Agent Engines (one per realm) with managed sessions; ${multi} multi-agent workflows (sequential, parallel, loop, coordinator).`],
    ["tools", "Tools", `${c.tools} typed function tools incl. the 7 wco-ge-skills; side effects are simulated so every demo is safe.`],
    ["grounding", "Grounding", "Vertex AI Search knowledge base per realm, Grounding with Google Search, BigQuery demo warehouse and synthetic systems of record."],
  ].map(([k, h, p]) => `<div class="bi"><h3><span class="dot" style="background:${BLOCK_COLORS[k]}"></span>${h}</h3><p>${esc(p)}</p></div>`).join("");
  $("#legend").innerHTML = STATUS_ORDER.map((k) => `<span>${legendHex(k, "#5f5d57").replace('width="14" height="15"', 'width="20" height="22"')}${esc(S.cat.statuses[k].label)}</span>`).join("")
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
      <div class="realm-head"><h2 style="color:${r.color}">${esc(r.name)}</h2><span class="muted">${n} agents · ${d} demo-ready</span><span class="kind" style="color:${r.color}">${r.kind}</span></div>
      <p class="realm-blurb">${esc(r.blurb)}</p>${securityBand(r.id)}<div class="clusters">${clusters}</div></section>`;
  };
  const by = Object.fromEntries(S.cat.realms.map((r) => [r.id, r]));
  const left = ["platform", "government", "smb"].filter((k) => by[k]).map((k) => realm(by[k])).join("");
  const right = ["enterprise", "delivery"].filter((k) => by[k]).map((k) => realm(by[k])).join("");
  const extra = S.cat.realms.filter((r) => !["platform", "government", "smb", "enterprise", "delivery"].includes(r.id)).map(realm).join("");
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
      tip.innerHTML = `<b>${esc(a.name)}</b>${esc(a.tagline)}<div class="t-meta">${esc(S.cat.statuses[a.status].label)} · ${TIER_LABEL[a.model]} · ${a.pattern}${a.aka ? " · " + esc(a.aka) : ""}</div>`;
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
    <div class="foot"><span class="tag ${a.model}">${TIER_LABEL[a.model]}</span><span class="tag">${esc(a.pattern)}</span><span class="tag">${esc(S.cat.statuses[a.status].label.split(" —")[0])}</span>
    <button class="primary" style="margin-left:auto;padding:5px 14px" data-open="${a.id}">Open demo</button></div></article>`;
}
function renderNavigator() {
  const list = [...S.agents.values()].filter(matches);
  const groups = S.cat.realms.map((r) => {
    const ag = list.filter((a) => a.realm === r.id);
    if (!ag.length) return "";
    return `<h2 class="group-title" style="color:${r.color}">${esc(r.name)} <span class="muted">(${ag.length})</span></h2><div class="cards">${ag.map(agentCard).join("")}</div>`;
  }).join("");
  $("#view-navigator").innerHTML = (list.length ? `<p class="muted">Showing ${list.length} of ${S.agents.size} agents. Search by industry, persona, problem or tool — e.g. “churn”, “permits”, “BigQuery”, “migration”.</p>` : `<p class="muted">No agents match these filters.</p>`) + groups;
  $$("[data-open]", $("#view-navigator")).forEach((b) => b.onclick = () => openAgent(b.dataset.open));
}
function chip(id) {
  const a = S.agents.get(id); if (!a) return "";
  const c = S.realmOf.get(id).color;
  return `<button class="agent-chip" data-open="${id}"><i style="background:${c}">${esc(a.code)}</i>${esc(a.name.split(" · ")[0])}</button>`;
}
function renderCompositions() {
  $("#view-compositions").innerHTML = `<p class="muted">Compositions show how hive agents are assembled into client solutions and internal workflows.</p>` + S.cat.compositions.map((c) => `
    <article class="comp"><div class="row" style="display:flex;gap:10px;align-items:baseline;flex-wrap:wrap"><h3>${esc(c.name)}</h3><span class="tag">${esc(c.kind)}</span><span class="tag">${esc(c.status)}</span></div>
    <p>${esc(c.summary)}</p>
    <div class="flow">${c.flow.map((s, i) => `${i ? '<span class="arrow">→</span>' : ""}<div class="step">${esc(s)}</div>`).join("")}</div>
    <div class="agent-chips">${c.agents.map(chip).join("")}</div>
    <div class="comp-blocks" style="margin-top:10px">${["models", "runtime", "tools", "grounding"].map((k) => `<div><b>${k}</b>${esc(c.blocks[k] || "")}</div>`).join("")}</div></article>`).join("");
  $$("[data-open]", $("#view-compositions")).forEach((b) => b.onclick = () => openAgent(b.dataset.open));
}
function renderSkills() {
  $("#view-skills").innerHTML = `<p class="muted">wco-ge-skills — atomic, reusable functions that underpin higher-level agents. Each runs on the cheapest model that can do the job (Flash-Lite with a JSON schema) or no model at all, and is also exposed over MCP.</p><div class="cards">` + S.cat.skills.map((s) => `
    <article class="card"><h3><code>${esc(s.id)}</code></h3><div>${esc(s.description)}</div>
    <div class="muted small">Tool: <code>${esc(s.tool)}</code></div>
    <div class="agent-chips">${s.used_by.map(chip).join("") || '<span class="muted small">not used yet</span>'}</div></article>`).join("") + `</div>`;
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
  if (author.endsWith("_concierge")) return "Realm concierge";
  if (author.endsWith("__loader")) return "Workflow loader";
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
  const tools = b.tools.map((t) => `<div class="item" data-tool="${esc(t.name)}"><div><code>${esc(t.name)}</code>${t.kind !== "function" ? ` <span class="kind">${esc(t.kind)}</span>` : ""}${t.step ? ` <span class="kind">${esc(t.step)}</span>` : ""}<div class="desc">${esc(t.summary)}</div></div><span class="cnt"></span></div>`).join("") || `<p class="muted">No function tools — this agent reasons over grounding and its specialists.</p>`;
  const groundKey = (g) => g.kind;
  const grounding = b.grounding.map((g) => `<div class="item" data-ground="${groundKey(g)}"><div><b>${esc(g.label)}</b>${g.step ? ` <span class="kind">${esc(g.step)}</span>` : ""}<div class="desc">${esc(g.detail)}</div></div><span class="cnt"></span></div>`).join("") || `<p class="muted">Grounded in the conversation and its tools only.</p>`;
  const steps = b.runtime.steps.length ? `<div class="steps">${b.runtime.steps.map((s) => `<div class="item" data-step="${esc(s.id)}"><div><b>${esc(s.name)}</b> <span class="tag ${s.model}">${TIER_LABEL[s.model]}</span>${s.agent_ref ? ` <span class="kind">AgentTool</span>` : ""}<div class="desc">${esc(s.role)}</div></div><span class="cnt"></span></div>`).join("")}</div>` : "";
  const patternDesc = { single: "LlmAgent with tools", sequential: "SequentialAgent pipeline", parallel: "ParallelAgent fan-out + synthesis", coordinator: "Coordinator LlmAgent calling specialists as AgentTools", loop: "LoopAgent draft ↔ critic" }[b.runtime.pattern];
  $("#p-blocks").innerHTML = `
    <div class="blk" id="blk-model"><h3><span class="sw" style="background:${BLOCK_COLORS.model}"></span>Model<span class="n" id="tok"></span></h3>
      <p><span class="tag ${b.model.tier}">${esc(b.model.label)}</span> <code>${esc(b.model.model_id)}</code></p>
      <p class="muted">${esc(b.model.why)}</p>
      ${b.model.also_uses.length ? `<p class="small">Steps also use: ${b.model.also_uses.map(esc).join(", ")}</p>` : ""}
      <p class="small muted">Tier policy: ${esc(b.model.policy)}</p></div>
    <div class="blk" id="blk-runtime"><h3><span class="sw" style="background:${BLOCK_COLORS.runtime}"></span>Runtime<span class="n" id="rt-n"></span></h3>
      <dl class="kv"><dt>Platform</dt><dd>${esc(b.runtime.label)}</dd><dt>Engine</dt><dd id="rt-engine">${esc(b.runtime.engine)}</dd>
      <dt>Region</dt><dd>${esc(b.runtime.region)}</dd><dt>Pattern</dt><dd>${esc(patternDesc)}</dd><dt>Sessions</dt><dd id="rt-session">${esc(b.runtime.sessions)}</dd></dl>${steps}</div>
    <div class="blk" id="blk-tools"><h3><span class="sw" style="background:${BLOCK_COLORS.tools}"></span>Tools<span class="n">${b.tools.length}</span></h3>${tools}</div>
    <div class="blk" id="blk-grounding"><h3><span class="sw" style="background:${BLOCK_COLORS.grounding}"></span>Grounding<span class="n">${b.grounding.length}</span></h3>${grounding}<div class="sources small" id="sources"></div></div>
    ${layersFor(a.realm).filter((l) => l.id === "google_security").map((l) => `<div class="blk blk-sec" style="--sec:${LAYER_COLORS[l.id]}"><h3>${SHIELD}${esc(l.name)}<span class="n">reference</span></h3>
      ${l.controls.map((c) => `<div class="item"><div><b>${esc(c.name)}</b><div class="desc">${esc(c.brief || firstSentence(c.role))}</div></div></div>`).join("")}
      <p class="small muted">${esc(l.note)}</p></div>`).join("")}
    ${a.kpis?.length ? `<div class="blk"><h3>Business KPIs</h3><ul class="small" style="margin:0;padding-left:18px">${a.kpis.map((k) => `<li>${esc(k)}</li>`).join("")}</ul></div>` : ""}
    ${a.related?.length ? `<div class="blk"><h3>Related agents</h3><div class="agent-chips">${a.related.map(chip).join("")}</div></div>` : ""}`;
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
  const r = S.realmOf.get(id);
  const cl = r.clusters.find((c) => c.id === a.cluster);
  S.open = id; S.files = []; renderFiles();
  $("#p-hex").innerHTML = miniHex(a, 54);
  $("#p-name").textContent = a.name;
  $("#p-tagline").textContent = a.tagline;
  $("#p-meta").innerHTML = `<span class="tag" style="color:${r.color}">${esc(r.name)}</span><span class="tag">${esc(cl?.name || a.cluster)}</span><span class="tag">${legendHex(a.status, r.color)} ${esc(S.cat.statuses[a.status].label)}</span>${a.aka ? `<span class="tag">${esc(a.aka)}</span>` : ""}<span class="tag ${a.model}">${TIER_LABEL[a.model]}</span>`;
  $("#p-about").innerHTML = `<summary>About this agent — ${esc(a.persona)}</summary><p>${esc(a.description)}</p><b class="small">Use cases</b><ul>${a.use_cases.map((u) => `<li>${esc(u)}</li>`).join("")}</ul><b class="small">Output</b><p>${esc(a.output)}</p>`;
  $("#samples").innerHTML = a.samples.map((s) => `<button class="sample" type="button">${esc(s)}</button>`).join("");
  $$("#samples .sample").forEach((b, i) => b.onclick = () => { $("#msg").value = a.samples[i]; send(); });
  $("#doc-btn").hidden = !a.sample_doc;
  renderBlocks(a);
  const sess = S.sessions.get(id);
  $("#chat").innerHTML = sess?.html || `<div class="empty-chat"><b>Live demo</b><br>Pick a sample prompt or write your own. The agent runs on Vertex AI Agent Engine; watch the building blocks on the right light up as it plans, calls tools and retrieves grounding.</div>`;
  $("#runtime-line").textContent = sess?.line || "";
  $("#panel").hidden = false; $("#scrim").hidden = false;
  document.body.style.overflow = "hidden";
  history.replaceState(null, "", "#" + id);
  setTimeout(() => $("#msg").focus(), 50);
  warm(a.realm);
}
function closeAgent() {
  saveChat();
  S.open = null;
  $("#panel").hidden = true; $("#scrim").hidden = true;
  document.body.style.overflow = "";
  history.replaceState(null, "", S.view === "hive" ? location.pathname : "#view=" + S.view);
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
  if (!line.textContent) line.textContent = "Waking the realm's Agent Engine…";
  try {
    const r = await fetch(`/api/warm/${realm}`, { method: "POST" });
    const j = await r.json();
    S.warm.set(realm, r.ok ? "ready" : "error");
    if (S.open && S.agents.get(S.open).realm === realm && line.textContent.startsWith("Waking")) {
      line.textContent = r.ok ? `Agent Engine ready (${j.seconds}s)` : `Engine: ${j.detail || "unavailable"}`;
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
  $("#rt-session").textContent = `Session ${j.session_id.slice(0, 12)}… (managed)`;
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
      btn.className = "ghost small preview-btn"; btn.type = "button"; btn.textContent = "Preview"; btn.dataset.preview = "1";
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
  work.innerHTML = `<summary>Agent work <span class="muted" data-sum></span></summary><div class="work-list"></div><div class="typing"><i></i><i></i><i></i></div>`;
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
  S.running = true; $("#send").disabled = true;
  $("#msg").value = ""; S.files = []; renderFiles();
  addUser(text, files);
  const work = turnContainer();
  const line = $("#runtime-line");
  const tokens = { prompt: 0, output: 0, thoughts: 0 };
  let lastAuthor = null, nEvents = 0, gotText = false;
  try {
    line.textContent = "Creating managed session…";
    const sess = await ensureSession(a);
    line.textContent = "Running on Agent Engine…";
    const resp = await fetch("/api/run", {
      method: "POST", headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ agent_id: a.id, session_id: sess.id, message: text, files }),
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
          addEv(work, "agent", `<b>${esc(nm)}</b> <span class="muted">is working</span>`);
          const m = ev.author.match(/__(\w+?)$/);
          if (m) pulse(`[data-step="${m[1]}"]`, "blk-runtime"); else pulse("#none", "blk-runtime");
        }
        handleEvent(a, work, ev, tokens, () => { gotText = true; });
      }
    }
    if (!gotText) addEv(work, "error", "The agent finished without a text answer.");
  } catch (e) {
    addEv(work, "error", `<b>Error</b> ${esc(e.message)}`);
    if (String(e.message).includes("session")) S.sessions.delete(a.id);
  } finally {
    $(".typing", work)?.remove();
    $("[data-sum]", work).textContent = `· ${$$(".ev", work).length} steps`;
    if ($$(".ev.call", work).length === 0 && $$(".ev.error", work).length === 0) work.open = false;
    S.running = false; $("#send").disabled = false;
    const sess = S.sessions.get(a.id); if (sess) { sess.html = $("#chat").innerHTML; sess.line = line.textContent; }
    $("#msg").focus();
  }

  function handleEvent(a, work, ev, tokens, onText) {
    const chat = $("#chat");
    switch (ev.type) {
      case "runtime":
        line.textContent = `Agent Engine · first event ${ev.first_event_s}s`; break;
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
        addEv(work, "result", `<details><summary><code>${esc(ev.name)}</code> returned ${status ? `<b>${esc(status)}</b>` : ""}${/simulated":\s*true/.test(ev.response) ? ' <span class="kind">simulated</span>' : ""}</summary><pre>${esc(pretty)}${ev.truncated ? "\n…" : ""}</pre></details>`);
        break;
      }
      case "grounding": {
        pulse(`[data-ground="${ev.kind}"]`, "blk-grounding");
        const src = ev.sources.map((s) => s.uri ? `<a href="${esc(s.uri)}" target="_blank" rel="noopener noreferrer">${esc(s.title || s.uri)}</a>` : esc(s.title)).join(" · ");
        addEv(work, "grounding", `<b>${ev.kind === "kb" ? "Knowledge base" : "Google Search"}</b> ${ev.queries?.length ? `<span class="muted">“${esc(ev.queries.join("”, “"))}”</span>` : ""}<div class="sources">${src}</div>`);
        if (src) $("#sources").innerHTML = `<b>Latest sources:</b> ${src}`;
        break;
      }
      case "usage":
        tokens.prompt += ev.prompt; tokens.output += ev.output; tokens.thoughts += ev.thoughts || 0;
        $("#tok").textContent = `${(tokens.prompt + tokens.output + tokens.thoughts).toLocaleString()} tokens this turn`;
        pulse("#none", "blk-model");
        break;
      case "thought":
        addEv(work, "usage", `<details><summary class="muted">thinking</summary><pre>${esc(ev.text)}</pre></details>`); break;
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
        d.innerHTML = `<span class="file-ext">${esc(ext)}</span><div><b>${esc(ev.name)}</b><div class="muted small">${(ev.size / 1024).toFixed(1)} KB · rendered by ${esc(stepName(a, ev.author))}</div></div><a class="primary" href="${url}" download="${esc(ev.name)}">Download</a>`;
        chat.insertBefore(d, null);
        addEv(work, "result", `<b>Deliverable</b> <code>${esc(ev.name)}</code> <span class="muted">saved to session state and offered for download</span>`);
        chat.scrollTop = chat.scrollHeight;
        break;
      }
      case "state":
        if (ev.keys.includes("client_material")) addEv(work, "grounding", `<b>Workflow loader</b> <span class="muted">put the referenced sample document into session state for every step</span>`);
        break;
      case "error":
        addEv(work, "error", `<b>Error</b> ${esc(ev.message)}`); break;
      case "done":
        line.textContent = `Agent Engine · ${ev.seconds}s · ${(tokens.prompt + tokens.output + tokens.thoughts).toLocaleString()} tokens (in ${tokens.prompt.toLocaleString()}, out ${tokens.output.toLocaleString()}${tokens.thoughts ? `, thinking ${tokens.thoughts.toLocaleString()}` : ""})`;
        break;
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
async function init() {
  mermaid.initialize({ startOnLoad: false, theme: "neutral", securityLevel: "strict" });
  const cat = await (await fetch("/api/catalog")).json();
  S.cat = cat;
  for (const r of cat.realms) for (const a of r.agents) { S.agents.set(a.id, a); S.realmOf.set(a.id, r); }
  $("#title").textContent = cat.title;
  renderHeader(); renderFilterChips(); renderHive();

  $$(".views button").forEach((b) => b.onclick = () => setView(b.dataset.view));
  $("#q").addEventListener("input", (e) => { S.filters.q = e.target.value.trim(); applyFilters(); });
  $("#clear-filters").onclick = () => {
    S.filters.q = ""; S.filters.status.clear(); S.filters.tier.clear(); $("#q").value = "";
    $$(".chip[aria-pressed]").forEach((c) => c.setAttribute("aria-pressed", "false")); applyFilters();
  };
  $("#p-close").onclick = closeAgent; $("#scrim").onclick = closeAgent;
  $("#preview-close").onclick = () => { $("#preview").hidden = true; $("#preview-frame").srcdoc = ""; };
  document.addEventListener("keydown", (e) => {
    if (e.key === "Escape") { if (!$("#preview").hidden) $("#preview-close").click(); else if (S.open) closeAgent(); }
  });
  $("#composer").addEventListener("submit", (e) => { e.preventDefault(); send(); });
  $("#msg").addEventListener("keydown", (e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } });
  $("#new-session").onclick = () => {
    if (!S.open) return;
    S.sessions.delete(S.open);
    $("#chat").innerHTML = `<div class="empty-chat">New session — the agent starts with a clean state.</div>`;
    $("#runtime-line").textContent = "";
  };
  $("#doc-btn").onclick = async () => {
    const a = S.agents.get(S.open);
    const r = await fetch(`/api/doc/${a.sample_doc}`);
    if (!r.ok) return;
    const j = await r.json();
    $("#msg").value = ($("#msg").value ? $("#msg").value + "\n\n" : `Here is the document "${j.title}":\n\n`) + j.text;
    $("#msg").focus();
  };
  $("#file").addEventListener("change", async (e) => {
    for (const f of e.target.files) {
      if (f.size > 7 * 1024 * 1024) { alert(`${f.name} is larger than 7 MB`); continue; }
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
init().catch((e) => { document.body.insertAdjacentHTML("afterbegin", `<p style="padding:20px;color:var(--danger)">Could not load the hive: ${esc(e.message)}</p>`); });
