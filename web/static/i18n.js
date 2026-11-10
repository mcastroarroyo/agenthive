/* Wursta Agent Hive — UI strings (EN/ES) and catalog localisation. Loaded before app.js and admin.js. */
"use strict";

const I18N = {
  en: {
    "view.hive": "Hive map", "view.navigator": "Use-case navigator", "view.compositions": "Compositions", "view.skills": "Skill library",
    "search": "Search agents, use cases, tools…", "clear": "Clear filters",
    "stat.agents": "agents", "stat.segments": "customer segments", "stat.live": "live demos", "stat.engines": "Agent Engines", "stat.tools": "function tools",
    "bi.models": "Models", "bi.runtime": "Runtime", "bi.tools": "Tools", "bi.grounding": "Grounding",
    "bi.models.p": "Gemini tiers by cost: Flash-Lite {lite} · Flash {flash} · Argon {argon} (only where deep reasoning is the product).",
    "bi.runtime.p": "{engines} Vertex AI Agent Engines (one per {term}) with managed sessions; {multi} multi-agent workflows (sequential, parallel, loop, coordinator).",
    "bi.tools.p": "{tools} typed function tools incl. the 7 wco-ge-skills; side effects are simulated so every demo is safe.",
    "bi.grounding.p": "Vertex AI Search knowledge base per {term}, Grounding with Google Search, BigQuery demo warehouse and synthetic systems of record.",
    "term.realm": "realm", "term.segment": "segment",
    "realm.agents": "{n} agents", "realm.demo": "{n} demo-ready",
    "sec.layer": "Security layer", "sec.waisentry": "Protected by WAISentry", "sec.open": "Open the WAISentry SOC demo", "sec.reference": "reference",
    "card.open": "Open demo",
    "nav.showing": "Showing {n} of {m} agents. Search by industry, persona, problem or tool — e.g. “churn”, “permits”, “BigQuery”, “migration”.",
    "nav.none": "No agents match these filters.",
    "comp.intro.internal": "Compositions show how hive agents are assembled into client solutions and internal workflows.",
    "comp.intro": "Compositions show how agents combine into end-to-end solutions.",
    "skills.intro": "wco-ge-skills — atomic, reusable functions that underpin higher-level agents. Each runs on the cheapest model that can do the job (Flash-Lite with a JSON schema) or no model at all, and is also exposed over MCP.",
    "skills.tool": "Tool", "skills.unused": "not used yet",
    "step.concierge": "{Term} concierge", "step.loader": "Workflow loader",
    "blk.model": "Model", "blk.runtime": "Runtime", "blk.tools": "Tools", "blk.grounding": "Grounding",
    "blk.notools": "No function tools — this agent reasons over grounding and its specialists.",
    "blk.noground": "Grounded in the conversation and its tools only.",
    "blk.also": "Steps also use:", "blk.policy": "Tier policy:", "blk.platform": "Platform", "blk.engine": "Engine",
    "blk.region": "Region", "blk.pattern": "Pattern", "blk.sessions": "Sessions", "blk.kpis": "Business KPIs", "blk.related": "Related agents",
    "pat.single": "LlmAgent with tools", "pat.sequential": "SequentialAgent pipeline", "pat.parallel": "ParallelAgent fan-out + synthesis",
    "pat.coordinator": "Coordinator LlmAgent calling specialists as AgentTools", "pat.loop": "LoopAgent draft ↔ critic",
    "tok.turn": "{n} tokens this turn",
    "about": "About this agent — {persona}", "about.uses": "Use cases", "about.output": "Output",
    "chat.empty": "<b>Live demo</b><br>Pick a sample prompt or write your own. The agent runs on Vertex AI Agent Engine; watch the building blocks on the right light up as it plans, calls tools and retrieves grounding.",
    "chat.new": "New session — the agent starts with a clean state.",
    "rt.waking": "Waking the {term}'s Agent Engine…", "rt.ready": "Agent Engine ready ({s}s)", "rt.engine": "Engine: {x}",
    "rt.session": "Creating managed session…", "rt.running": "Running on Agent Engine…", "rt.first": "Agent Engine · first event {s}s",
    "rt.done": "Agent Engine · {s}s · {tok} tokens", "rt.budget": "{used} of {limit} tokens used in this demo session",
    "sess.managed": "Session {id}… (managed)",
    "work.title": "Agent work", "work.steps": "· {n} steps", "work.working": "is working", "work.returned": "returned",
    "work.simulated": "simulated", "work.kb": "Knowledge base", "work.gs": "Google Search", "work.sources": "Latest sources:",
    "work.thinking": "thinking", "work.deliverable": "Deliverable", "work.saved": "saved to session state and offered for download",
    "work.loader": "put the referenced sample document into session state for every step", "work.notext": "The agent finished without a text answer.",
    "work.error": "Error", "file.by": "rendered by {who}", "file.download": "Download",
    "msg.ph": "Ask the agent… (Enter to send, Shift+Enter for a new line)", "msg.attach": "Attach file", "msg.doc": "Insert sample document",
    "msg.new": "New session", "msg.run": "Run", "msg.docintro": "Here is the document \"{t}\":", "msg.toobig": "{f} is larger than 7 MB",
    "prev.title": "Prototype preview", "prev.note": "sandboxed — scripts allowed, no network to this app", "prev.btn": "Preview",
    "login.lead": "Live Google Cloud agent demos for every industry.",
    "login.cta": "Sign in with your Google account — Gmail or Google Workspace — to try the demos.",
    "login.privacy": "When you sign in, Wursta records your email, your sign-ins, the demos you run and your ratings to improve this site. Every demo uses synthetic data: please don't enter personal or confidential information.",
    "login.busy": "Signing in…", "login.failed": "Sign-in failed: {e}", "login.privacylink": "Privacy notice",
    "user.signout": "Sign out", "user.admin": "Admin", "lang": "Language",
    "fb.title": "How was this demo?", "fb.agent": "{agent}", "fb.1": "Very bad", "fb.2": "Bad", "fb.3": "OK", "fb.4": "Good", "fb.5": "Very good",
    "fb.comment": "Tell us more (optional)", "fb.send": "Send", "fb.skip": "Skip", "fb.thanks": "Thanks for your feedback!",
    "load.fail": "Could not load the hive: {e}",
  },
  es: {
    "view.hive": "Mapa de agentes", "view.navigator": "Casos de uso", "view.compositions": "Composiciones", "view.skills": "Biblioteca de skills",
    "search": "Busca agentes, casos de uso, herramientas…", "clear": "Quitar filtros",
    "stat.agents": "agentes", "stat.segments": "segmentos de clientes", "stat.live": "demos en vivo", "stat.engines": "Agent Engines", "stat.tools": "herramientas",
    "bi.models": "Modelos", "bi.runtime": "Runtime", "bi.tools": "Herramientas", "bi.grounding": "Grounding",
    "bi.models.p": "Niveles de Gemini por costo: Flash-Lite {lite} · Flash {flash} · Argon {argon} (solo donde el razonamiento profundo es el producto).",
    "bi.runtime.p": "{engines} Vertex AI Agent Engines (uno por {term}) con sesiones gestionadas; {multi} flujos multiagente (secuencial, paralelo, bucle, coordinador).",
    "bi.tools.p": "{tools} herramientas tipadas, incluidas las 7 wco-ge-skills; las acciones son simuladas para que cada demo sea segura.",
    "bi.grounding.p": "Base de conocimiento en Vertex AI Search por {term}, Grounding con Google Search, almacén de datos en BigQuery y sistemas de registro sintéticos.",
    "term.realm": "reino", "term.segment": "segmento",
    "realm.agents": "{n} agentes", "realm.demo": "{n} listos para demo",
    "sec.layer": "Capa de seguridad", "sec.waisentry": "Protegido por WAISentry", "sec.open": "Abrir la demo de WAISentry SOC", "sec.reference": "referencia",
    "card.open": "Abrir demo",
    "nav.showing": "Mostrando {n} de {m} agentes. Busca por industria, rol, problema o herramienta — p. ej. “churn”, “permisos”, “BigQuery”, “migración”.",
    "nav.none": "Ningún agente coincide con estos filtros.",
    "comp.intro.internal": "Las composiciones muestran cómo se combinan los agentes en soluciones para clientes y flujos internos.",
    "comp.intro": "Las composiciones muestran cómo se combinan los agentes en soluciones de punta a punta.",
    "skills.intro": "wco-ge-skills: funciones atómicas y reutilizables que sostienen a los agentes de nivel superior. Cada una usa el modelo más económico que resuelve la tarea (Flash-Lite con un esquema JSON) o ninguno, y también se expone por MCP.",
    "skills.tool": "Herramienta", "skills.unused": "aún no se usa",
    "step.concierge": "Concierge del {term}", "step.loader": "Cargador del flujo",
    "blk.model": "Modelo", "blk.runtime": "Runtime", "blk.tools": "Herramientas", "blk.grounding": "Grounding",
    "blk.notools": "Sin herramientas de función: este agente razona sobre su grounding y sus especialistas.",
    "blk.noground": "Se basa solo en la conversación y sus herramientas.",
    "blk.also": "Los pasos también usan:", "blk.policy": "Política de nivel:", "blk.platform": "Plataforma", "blk.engine": "Engine",
    "blk.region": "Región", "blk.pattern": "Patrón", "blk.sessions": "Sesiones", "blk.kpis": "KPIs de negocio", "blk.related": "Agentes relacionados",
    "pat.single": "LlmAgent con herramientas", "pat.sequential": "Pipeline SequentialAgent", "pat.parallel": "ParallelAgent en paralelo + síntesis",
    "pat.coordinator": "LlmAgent coordinador que llama especialistas como AgentTools", "pat.loop": "LoopAgent borrador ↔ crítico",
    "tok.turn": "{n} tokens en este turno",
    "about": "Sobre este agente — {persona}", "about.uses": "Casos de uso", "about.output": "Resultado",
    "chat.empty": "<b>Demo en vivo</b><br>Elige un ejemplo o escribe tu propia pregunta. El agente corre en Vertex AI Agent Engine; mira cómo se encienden los bloques de la derecha mientras planifica, llama herramientas y consulta su grounding.",
    "chat.new": "Nueva sesión: el agente empieza desde cero.",
    "rt.waking": "Despertando el Agent Engine del {term}…", "rt.ready": "Agent Engine listo ({s}s)", "rt.engine": "Engine: {x}",
    "rt.session": "Creando la sesión gestionada…", "rt.running": "Ejecutando en Agent Engine…", "rt.first": "Agent Engine · primer evento {s}s",
    "rt.done": "Agent Engine · {s}s · {tok} tokens", "rt.budget": "{used} de {limit} tokens usados en esta sesión de demo",
    "sess.managed": "Sesión {id}… (gestionada)",
    "work.title": "Trabajo del agente", "work.steps": "· {n} pasos", "work.working": "está trabajando", "work.returned": "devolvió",
    "work.simulated": "simulado", "work.kb": "Base de conocimiento", "work.gs": "Google Search", "work.sources": "Últimas fuentes:",
    "work.thinking": "razonamiento", "work.deliverable": "Entregable", "work.saved": "guardado en la sesión y listo para descargar",
    "work.loader": "cargó el documento de ejemplo en el estado de la sesión para cada paso", "work.notext": "El agente terminó sin una respuesta de texto.",
    "work.error": "Error", "file.by": "generado por {who}", "file.download": "Descargar",
    "msg.ph": "Pregunta al agente… (Enter para enviar, Shift+Enter para nueva línea)", "msg.attach": "Adjuntar archivo", "msg.doc": "Insertar documento de ejemplo",
    "msg.new": "Nueva sesión", "msg.run": "Ejecutar", "msg.docintro": "Este es el documento \"{t}\":", "msg.toobig": "{f} pesa más de 7 MB",
    "prev.title": "Vista previa del prototipo", "prev.note": "aislada: permite scripts, sin red hacia esta app", "prev.btn": "Vista previa",
    "login.lead": "Demos en vivo de agentes de Google Cloud para cada industria.",
    "login.cta": "Inicia sesión con tu cuenta de Google —Gmail o Google Workspace— para probar las demos.",
    "login.privacy": "Al iniciar sesión, Wursta registra tu correo, tus ingresos, las demos que pruebas y tus calificaciones para mejorar este sitio. Todas las demos usan datos sintéticos: no ingreses información personal ni confidencial.",
    "login.busy": "Iniciando sesión…", "login.failed": "No se pudo iniciar sesión: {e}", "login.privacylink": "Aviso de privacidad",
    "user.signout": "Cerrar sesión", "user.admin": "Admin", "lang": "Idioma",
    "fb.title": "¿Qué te pareció este demo?", "fb.agent": "{agent}", "fb.1": "Muy malo", "fb.2": "Malo", "fb.3": "Regular", "fb.4": "Bueno", "fb.5": "Muy bueno",
    "fb.comment": "Cuéntanos más (opcional)", "fb.send": "Enviar", "fb.skip": "Omitir", "fb.thanks": "¡Gracias por tu opinión!",
    "load.fail": "No se pudo cargar el hive: {e}",
  },
};

let LANG = (() => {
  try { const v = localStorage.getItem("hive_lang"); if (v === "en" || v === "es") return v; } catch {}
  return (navigator.language || "en").toLowerCase().startsWith("es") ? "es" : "en";
})();

function t(key, vars = {}) {
  const s = (I18N[LANG] && I18N[LANG][key]) ?? I18N.en[key] ?? key;
  return s.replace(/\{(\w+)\}/g, (_, k) => (k in vars ? vars[k] : `{${k}}`));
}

function setLang(lang) {
  LANG = lang;
  try { localStorage.setItem("hive_lang", lang); } catch {}
  document.documentElement.lang = lang;
}

/* Static text in index.html / admin.html: data-i18n (textContent) and data-i18n-placeholder. */
function applyStatic(root = document) {
  root.querySelectorAll("[data-i18n]").forEach((el) => { el.textContent = t(el.dataset.i18n); });
  root.querySelectorAll("[data-i18n-placeholder]").forEach((el) => { el.placeholder = t(el.dataset.i18nPlaceholder); });
}

/* Merge the catalog's translations (cat.i18n[lang]) into a copy of the catalog. */
function localize(cat, lang) {
  const tr = (cat.i18n || {})[lang];
  const c = JSON.parse(JSON.stringify(cat));
  if (!tr) return c;
  const pick = (dst, src, keys) => { if (src) for (const k of keys) if (src[k] != null && src[k] !== "") dst[k] = src[k]; };
  pick(c, tr, ["title", "subtitle"]);
  for (const [k, v] of Object.entries(tr.statuses || {})) if (c.statuses[k]) pick(c.statuses[k], v, ["label", "description"]);
  for (const r of c.realms) {
    const sr = (tr.segments || {})[r.id];
    pick(r, sr, ["name", "blurb"]);
    for (const cl of r.clusters) pick(cl, ((sr || {}).clusters || {})[cl.id], ["name", "blurb"]);
    for (const a of r.agents) {
      const ta = (tr.agents || {})[a.id];
      if (!ta) continue;
      pick(a, ta, ["name", "tagline", "description", "persona", "use_cases", "output", "samples", "kpis", "model_reason"]);
      if (ta.model_reason) a.blocks.model.why = ta.model_reason;
      for (const s of a.steps || []) pick(s, (ta.steps || {})[s.id], ["name", "role"]);
      for (const s of a.blocks.runtime.steps || []) pick(s, (ta.steps || {})[s.id], ["name", "role"]);
    }
  }
  for (const comp of c.compositions) {
    const tc = (tr.compositions || {})[comp.id];
    pick(comp, tc, ["name", "status", "summary", "flow"]);
    if (tc && tc.blocks) comp.blocks = { ...comp.blocks, ...tc.blocks };
  }
  for (const l of c.security_layers || []) {
    const tl = (tr.security_layers || {})[l.id];
    pick(l, tl, ["name", "note", "summary"]);
    if (tl && tl.controls) l.controls = l.controls.map((ctl, i) => ({ ...ctl, ...(tl.controls[i] || {}) }));
  }
  for (const s of c.skills || []) pick(s, ((tr.skills || {})[s.id] || null) && { description: tr.skills[s.id] }, ["description"]);
  return c;
}
