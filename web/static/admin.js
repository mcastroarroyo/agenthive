/* Hive admin — sign-ins, demos run, ratings and usage limits (showcase edition). */
"use strict";

Object.assign(I18N.en, {
  "adm.title": "Hive admin", "adm.sub": "Who signed in, which demos they tried, how they rated them, and the usage limits.",
  "adm.back": "Back to the hive", "adm.refresh": "Refresh",
  "adm.t.overview": "Overview", "adm.t.users": "Users", "adm.t.runs": "Demos run", "adm.t.feedback": "Ratings", "adm.t.logins": "Sign-ins", "adm.t.limits": "Limits",
  "k.users": "people signed in", "k.today": "active today", "k.runs": "demo runs (14 days)", "k.tokens": "tokens today", "k.rating": "average rating", "k.ratings": "{n} ratings",
  "k.ofLimit": "of {n} daily limit", "k.paused": "Demos are PAUSED (kill switch)",
  "o.days": "Demo runs per day (UTC)", "o.top": "Ratings by agent",
  "c.email": "Email", "c.name": "Name", "c.domain": "Domain", "c.first": "First seen", "c.last": "Last seen", "c.logins": "Sign-ins",
  "c.runs": "Runs", "c.tokens": "Tokens", "c.agents": "Agents tried", "c.top": "Most used", "c.when": "When", "c.user": "User",
  "c.segment": "Segment", "c.agent": "Agent", "c.secs": "Seconds", "c.status": "Status", "c.lang": "Lang", "c.sample": "Sample",
  "c.rating": "Rating", "c.comment": "Comment", "c.count": "Ratings", "c.avg": "Average", "c.ua": "Browser",
  "f.user": "Filter by email", "f.all": "All users", "f.show": "Show",
  "l.enabled": "Demos enabled", "l.session": "Tokens per demo session", "l.user": "Tokens per person per day", "l.runs": "Runs per person per day",
  "l.app": "Tokens per day, whole app", "l.calls": "Model calls per turn", "l.save": "Save limits", "l.saved": "Saved",
  "l.help.session": "The engine stops answering in a session once it reaches this.", "l.help.app": "Everyone together, per UTC day. Turn off \"Demos enabled\" to stop all new runs at once.",
  "none": "Nothing yet.", "forbidden": "Admins only.",
});
Object.assign(I18N.es, {
  "adm.title": "Admin del hive", "adm.sub": "Quién ha entrado, qué demos ha probado, cómo las calificó y los límites de uso.",
  "adm.back": "Volver al hive", "adm.refresh": "Actualizar",
  "adm.t.overview": "Resumen", "adm.t.users": "Usuarios", "adm.t.runs": "Demos ejecutadas", "adm.t.feedback": "Calificaciones", "adm.t.logins": "Ingresos", "adm.t.limits": "Límites",
  "k.users": "personas registradas", "k.today": "activas hoy", "k.runs": "demos ejecutadas (14 días)", "k.tokens": "tokens hoy", "k.rating": "calificación promedio", "k.ratings": "{n} calificaciones",
  "k.ofLimit": "de un límite diario de {n}", "k.paused": "Las demos están PAUSADAS (interruptor general)",
  "o.days": "Demos por día (UTC)", "o.top": "Calificaciones por agente",
  "c.email": "Correo", "c.name": "Nombre", "c.domain": "Dominio", "c.first": "Primer ingreso", "c.last": "Último ingreso", "c.logins": "Ingresos",
  "c.runs": "Demos", "c.tokens": "Tokens", "c.agents": "Agentes probados", "c.top": "Más usados", "c.when": "Cuándo", "c.user": "Usuario",
  "c.segment": "Segmento", "c.agent": "Agente", "c.secs": "Segundos", "c.status": "Estado", "c.lang": "Idioma", "c.sample": "Ejemplo",
  "c.rating": "Calificación", "c.comment": "Comentario", "c.count": "Calificaciones", "c.avg": "Promedio", "c.ua": "Navegador",
  "f.user": "Filtrar por correo", "f.all": "Todos los usuarios", "f.show": "Ver",
  "l.enabled": "Demos habilitadas", "l.session": "Tokens por sesión de demo", "l.user": "Tokens por persona por día", "l.runs": "Demos por persona por día",
  "l.app": "Tokens por día, toda la app", "l.calls": "Llamadas al modelo por turno", "l.save": "Guardar límites", "l.saved": "Guardado",
  "l.help.session": "El motor deja de responder en una sesión cuando llega a este valor.", "l.help.app": "Todos juntos, por día UTC. Desactiva \"Demos habilitadas\" para detener todas las ejecuciones nuevas de inmediato.",
  "none": "Aún no hay datos.", "forbidden": "Solo administradores.",
});

const $ = (s, el = document) => el.querySelector(s);
const $$ = (s, el = document) => [...el.querySelectorAll(s)];
const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
const num = (n) => Number(n || 0).toLocaleString(LANG === "es" ? "es" : "en");
const when = (iso) => iso ? new Date(iso).toLocaleString(LANG === "es" ? "es" : "en", { dateStyle: "medium", timeStyle: "short" }) : "";
const A = { tab: "overview", data: {}, userFilter: "" };

async function api(path, opts) {
  const r = await fetch(path, opts);
  if (r.status === 401 || r.status === 403) { document.querySelector(".adm-main").innerHTML = `<p>${esc(t("forbidden"))}</p>`; throw new Error("forbidden"); }
  if (!r.ok) throw new Error((await r.json().catch(() => ({}))).detail || r.statusText);
  return r.json();
}

function table(cols, rows) {
  if (!rows.length) return `<p class="muted">${esc(t("none"))}</p>`;
  return `<div class="tbl-wrap"><table class="tbl"><thead><tr>${cols.map((c) => `<th class="${c.cls || ""}">${esc(t(c.h))}</th>`).join("")}</tr></thead>
    <tbody>${rows.map((r) => `<tr>${cols.map((c) => `<td class="${c.cls || ""}">${c.v(r)}</td>`).join("")}</tr>`).join("")}</tbody></table></div>`;
}

function renderOverview() {
  const s = A.data.summary; if (!s) return;
  const today = s.days[0] || { tokens: 0, runs: 0 };
  const pct = Math.min(100, Math.round(100 * today.tokens / (s.limits.app_daily_tokens || 1)));
  const runs14 = s.days.reduce((n, d) => n + d.runs, 0);
  const max = Math.max(1, ...s.days.map((d) => d.runs));
  $("#tab-overview").innerHTML = `${s.limits.enabled ? "" : `<p class="pill error" style="margin-bottom:10px">${esc(t("k.paused"))}</p>`}
    <div class="kpis">
      <div class="kpi"><b>${num(s.users)}</b><span>${esc(t("k.users"))}</span></div>
      <div class="kpi"><b>${num(s.users_today)}</b><span>${esc(t("k.today"))}</span></div>
      <div class="kpi"><b>${num(runs14)}</b><span>${esc(t("k.runs"))}</span></div>
      <div class="kpi"><b>${num(today.tokens)}</b><span>${esc(t("k.tokens"))} · ${esc(t("k.ofLimit", { n: num(s.limits.app_daily_tokens) }))}</span><div class="bar"><i style="width:${pct}%"></i></div></div>
      <div class="kpi"><b>${s.avg_rating ?? "—"}</b><span>${esc(t("k.rating"))} · ${esc(t("k.ratings", { n: num(s.feedback) }))}</span></div>
    </div>
    <div class="panel-box"><h2>${esc(t("o.days"))}</h2><div class="days">${[...s.days].reverse().map((d) => `<div class="day" title="${d.day}: ${d.runs} · ${num(d.tokens)} tokens"><span>${d.runs || ""}</span><i style="height:${Math.round(100 * d.runs / max)}%"></i><span>${d.day.slice(5)}</span></div>`).join("")}</div></div>
    <div class="panel-box"><h2>${esc(t("o.top"))}</h2>${table([
      { h: "c.agent", v: (r) => esc(r.agent) }, { h: "c.count", cls: "num", v: (r) => num(r.count) },
      { h: "c.avg", cls: "num", v: (r) => `<span class="stars">${r.avg.toFixed(2)}</span>` }], s.ratings_by_agent)}</div>`;
}

function renderUsers() {
  const rows = A.data.users || [];
  $("#tab-users").innerHTML = table([
    { h: "c.email", v: (u) => `<button class="linkish" data-user="${esc(u.email)}">${esc(u.email)}</button>` },
    { h: "c.name", v: (u) => esc(u.name) }, { h: "c.domain", v: (u) => esc(u.domain) },
    { h: "c.first", v: (u) => esc(when(u.first_seen)) }, { h: "c.last", v: (u) => esc(when(u.last_seen)) },
    { h: "c.logins", cls: "num", v: (u) => num(u.logins) }, { h: "c.runs", cls: "num", v: (u) => num(u.runs) },
    { h: "c.tokens", cls: "num", v: (u) => num(u.tokens) }, { h: "c.agents", cls: "num", v: (u) => num(u.agents_tried) },
    { h: "c.top", v: (u) => esc((u.top_agents || []).map(([k, n]) => `${k} ×${n}`).join(", ")) }], rows);
  $$("[data-user]").forEach((b) => b.onclick = () => { A.userFilter = b.dataset.user; setTab("runs"); });
}

async function renderRuns() {
  const box = $("#tab-runs");
  const q = A.userFilter ? `?email=${encodeURIComponent(A.userFilter)}` : "";
  const runs = (await api(`/api/admin/runs${q}`)).runs;
  const users = (A.data.users || []).map((u) => u.email);
  box.innerHTML = `<div class="adm-filter"><label>${esc(t("f.user"))} <select id="uf"><option value="">${esc(t("f.all"))}</option>${users.map((e) => `<option ${e === A.userFilter ? "selected" : ""}>${esc(e)}</option>`).join("")}</select></label></div>`
    + table([
      { h: "c.when", v: (r) => esc(when(r.ts)) }, { h: "c.user", v: (r) => esc(r.email) }, { h: "c.segment", v: (r) => esc(r.segment) },
      { h: "c.agent", v: (r) => esc(r.agent || r.agent_id) }, { h: "c.tokens", cls: "num", v: (r) => num(r.tokens) },
      { h: "c.secs", cls: "num", v: (r) => esc(r.seconds) }, { h: "c.status", v: (r) => `<span class="pill ${r.status === "ok" ? "ok" : "error"}" title="${esc(r.error || "")}">${esc(r.status)}</span>` },
      { h: "c.lang", v: (r) => esc(r.lang) }, { h: "c.sample", v: (r) => r.sample ? "✓" : "" }], runs);
  $("#uf").onchange = (e) => { A.userFilter = e.target.value; renderRuns(); };
}

async function renderFeedback() {
  const fb = (await api("/api/admin/feedback")).feedback;
  $("#tab-feedback").innerHTML = table([
    { h: "c.when", v: (r) => esc(when(r.ts)) }, { h: "c.user", v: (r) => esc(r.email) }, { h: "c.agent", v: (r) => esc(r.agent || r.agent_id) },
    { h: "c.rating", cls: "num", v: (r) => `<span class="stars">${"★".repeat(r.rating)}${"☆".repeat(5 - r.rating)}</span>` },
    { h: "c.comment", cls: "wrap", v: (r) => esc(r.comment) }, { h: "c.lang", v: (r) => esc(r.lang) }], fb);
}

async function renderLogins() {
  const rows = (await api("/api/admin/logins")).logins;
  $("#tab-logins").innerHTML = table([
    { h: "c.when", v: (r) => esc(when(r.ts)) }, { h: "c.email", v: (r) => esc(r.email) }, { h: "c.lang", v: (r) => esc(r.lang) },
    { h: "c.ua", cls: "wrap", v: (r) => esc(r.ua) }], rows);
}

function renderLimits() {
  const l = A.data.summary?.limits; if (!l) return;
  const field = (k, label, help = "") => `<label for="lim-${k}">${esc(t(label))}</label><input type="number" id="lim-${k}" value="${l[k]}" min="1" step="1">${help ? `<p class="muted small help">${esc(t(help))}</p>` : ""}`;
  $("#tab-limits").innerHTML = `<div class="panel-box"><form class="limits-form" id="lim">
      <label for="lim-enabled">${esc(t("l.enabled"))}</label><input type="checkbox" id="lim-enabled" ${l.enabled ? "checked" : ""}>
      ${field("session_tokens", "l.session", "l.help.session")}${field("user_daily_tokens", "l.user")}${field("user_daily_runs", "l.runs")}
      ${field("app_daily_tokens", "l.app", "l.help.app")}${field("max_llm_calls", "l.calls")}
      <div><button class="primary" type="submit">${esc(t("l.save"))}</button><span class="saved" id="lim-ok" hidden>${esc(t("l.saved"))}</span></div>
    </form></div>`;
  $("#lim").onsubmit = async (e) => {
    e.preventDefault();
    const body = { enabled: $("#lim-enabled").checked };
    for (const k of ["session_tokens", "user_daily_tokens", "user_daily_runs", "app_daily_tokens", "max_llm_calls"]) body[k] = +$("#lim-" + k).value;
    const j = await api("/api/admin/limits", { method: "PUT", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
    A.data.summary.limits = j.limits; $("#lim-ok").hidden = false; setTimeout(() => { $("#lim-ok").hidden = true; }, 1600);
  };
}

function setTab(tab) {
  A.tab = tab;
  $$(".adm-tabs button").forEach((b) => b.setAttribute("aria-selected", b.dataset.tab === tab));
  $$(".adm-main > section").forEach((s) => { s.hidden = s.id !== "tab-" + tab; });
  ({ overview: renderOverview, users: renderUsers, runs: renderRuns, feedback: renderFeedback, logins: renderLogins, limits: renderLimits })[tab]();
}

async function load() {
  const [summary, users] = await Promise.all([api("/api/admin/summary"), api("/api/admin/users")]);
  A.data.summary = summary; A.data.users = users.users;
  setTab(A.tab);
}

function paintLang() {
  setLang(LANG); applyStatic();
  $$("[data-lang]").forEach((b) => { b.setAttribute("aria-pressed", b.dataset.lang === LANG); b.onclick = () => { setLang(b.dataset.lang); paintLang(); setTab(A.tab); }; });
}

paintLang();
$$(".adm-tabs button").forEach((b) => b.onclick = () => setTab(b.dataset.tab));
$("#refresh").onclick = () => load();
load().catch((e) => { if (e.message !== "forbidden") $(".adm-main").insertAdjacentHTML("afterbegin", `<p style="color:var(--danger)">${esc(e.message)}</p>`); });
