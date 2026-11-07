# Architecture

```mermaid
flowchart LR
  user([Wursta presenter / client]) -->|IAP sign-in| web[Cloud Run · agenthive-web<br/>hive UI + SSE proxy]
  web -->|create session · stream query| ae1[Agent Engine · Platform Core]
  web --> ae2[Agent Engine · Government]
  web --> ae3[Agent Engine · Enterprise]
  web --> ae4[Agent Engine · SMB]
  web --> ae5[Agent Engine · Delivery Engine]
  subgraph engine[Each Agent Engine]
    router[HiveRouter] --> a1[LlmAgent]
    router --> a2[SequentialAgent / ParallelAgent / LoopAgent]
    router --> a3[Coordinator + AgentTools]
  end
  ae1 -.-> engine
  engine -->|Gemini Flash-Lite / Flash / Argon<br/>location: global| gemini[(Vertex AI Gemini)]
  engine --> vais[(Vertex AI Search<br/>1 data store per realm)]
  engine --> gs[(Google Search grounding)]
  engine --> bq[(BigQuery<br/>agenthive_demo)]
  engine --> sandbox[(Gemini code execution)]
```

## Decisions

| Decision | Why |
|---|---|
| **One engine per realm, router inside** | Realms deploy and scale independently; ~20 agents share one warm container instead of 90 cold ones. Sessions are pinned to an agent, so the UI talks to "an agent", not to the router. |
| **Catalog-driven factory** | Agents are data. The UI, the deployed agents and the tests all read the same YAML, so what you see in the hive is what runs. |
| **Instruction providers** | Instructions are callables: they bypass ADK `{var}` templating (safe for JSON/code examples) and fill `{{output_key}}` from session state for pipeline steps. |
| **Cheapest model tier that works** | Flash-Lite for skills and routing, Flash by default, Argon reserved for coordinator/architecture/legal-risk reasoning. Tiers are env-overridable. |
| **Gemini on `global`** | Flash, Flash-Lite and Argon are served from the global endpoint; the model client is pinned there while Agent Engine runs in the region. |
| **Simulated side effects** | Tools that would send, create or move things return `simulated: true`. Demos are safe to run in front of clients. |
| **Synthetic data only** | Public repository; fictional organisations and records; client work is described generically. |
| **IAP in front of Cloud Run** | Only signed-in members of the allowed domain can run demos; a per-user rate limit caps Gemini spend. |

## Known follow-ups

- ADK 2.x marks `SequentialAgent`/`ParallelAgent`/`LoopAgent` as deprecated in favour of `Workflow`, which cannot yet
  be a sub-agent of an agent tree; migrate when ADK supports it.
- Register selected agents in Gemini Enterprise (one `adkAgentDefinition` per engine, `@code` routing).
- GitHub Actions deploy via Workload Identity Federation (CI currently runs the offline tests).
