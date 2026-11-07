# The Wursta Agent Hive

An interactive menu of **live agent demos**. Every hex in the hive is a Google ADK agent running on
**Vertex AI Agent Engine**; open one, pick a sample prompt and watch its four building blocks — **Model, Runtime,
Tools, Grounding** — light up as it plans, calls tools and retrieves knowledge.

- **Realms**: Government, Enterprise (financial, healthcare, telco, retail, logistics), SMB — plus the internal
  Platform Core (with the Pantheon advisory suite) and the Wursta Delivery Engine (WurstaBots, Atlas migration suite,
  innovation pipeline).
- **Compositions**: Pantheon strategy engagement, Atlas migration pipeline, Citizen Services Framework (proposed),
  real-estate enterprise sync (proposal), meeting-intelligence loop.
- **Skill library**: the seven `wco-ge-skills`, reused by agents and exposed over MCP.

All organisations, people and records in this repository are **synthetic**.

## The four ADK building blocks

| Block | How the hive implements it |
|---|---|
| **Models** | `agenthive/models.py` — three Gemini tiers. *Flash-Lite* for routing/extraction/templating, *Flash* by default, *Gemini 4 Argon* only where deep planning or synthesis is the product (Hermes, Daedalus, …). Every agent states why it uses its tier. |
| **Runtime** | One **Agent Engine** per realm (`deploy/deploy_engines.py`) hosting a `HiveRouter` that pins each session to one agent (`@code` prefix or session state). Managed sessions, Cloud Trace telemetry, scale-to-zero. Multi-agent patterns: `SequentialAgent`, `ParallelAgent`, `LoopAgent`, coordinator with `AgentTool`. |
| **Tools** | `agenthive/tools/` — typed Python function tools (docstrings are the tool descriptions), the `wco-ge-skills` library, Gemini code execution sandbox, BigQuery toolset. Side effects are simulated so every demo is safe. |
| **Grounding** | A **Vertex AI Search** data store per realm (`agenthive/grounding/corpus/<realm>`), **Grounding with Google Search**, a **BigQuery** demo warehouse, and synthetic systems of record behind tools. |

## Repository layout

```
agenthive/                  Python package shipped to Agent Engine
  catalog/hive.yaml         realms, clusters, compositions, skills
  catalog/realms/*.yaml     one entry per agent (identity, 4 blocks, instruction, samples, KPIs)
  agents/factory.py         catalog entry -> ADK agent (single / sequential / parallel / loop / coordinator)
  router.py                 HiveRouter: one engine per realm, one agent per session
  models.py                 model tiers (Flash-Lite / Flash / Argon)
  tools/                    function tools + fixtures (synthetic data) + sample documents
  grounding/                Vertex AI Search, Google Search, BigQuery wiring + KB corpus + BQ schemas
  mcp_server.py             wco-ge-skills over MCP
web/                        FastAPI + vanilla JS hive UI (Cloud Run behind IAP)
deploy/                     bootstrap, KB sync, BigQuery seed, engine + web deploys, local runner
docs/                       architecture and how to add agents
tests/                      catalog integrity + every agent builds offline
```

## Run it

```bash
python3.13 -m venv .venv && .venv/bin/pip install -e ".[web,dev]"
HIVE_OFFLINE=1 HIVE_PROJECT=test .venv/bin/pytest -q          # offline checks
```

Cloud setup (one project, everything parameterised — no IDs in this repo):

```bash
export HIVE_PROJECT=<your-project>
deploy/bootstrap.sh                                            # APIs, service accounts, bucket, dataset, data stores
.venv/bin/python deploy/sync_kb.py                             # corpus -> Vertex AI Search
.venv/bin/python deploy/seed_bigquery.py                       # synthetic warehouse -> BigQuery
GCLOUD_ACCESS_TOKEN=$(gcloud auth print-access-token) .venv/bin/python deploy/deploy_engines.py   # 1 engine / realm
HIVE_IAP_MEMBERS=domain:<your-domain> deploy/deploy_web.sh      # UI on Cloud Run + IAP
```

Try one agent locally through the same router:

```bash
GCLOUD_ACCESS_TOKEN=$(gcloud auth print-access-token) .venv/bin/python deploy/local_run.py proteus "ROI of a $180k project saving 6 FTE?"
```

## Adding an agent

Add a YAML entry and (optionally) tools — no glue code. See [docs/adding-agents.md](docs/adding-agents.md).
