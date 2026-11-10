# The Wursta Agent Hive

An interactive menu of **live agent demos**. Every hex in the hive is a Google ADK agent running on
**Vertex AI Agent Engine**; open one, pick a sample prompt and watch its four building blocks — **Model, Runtime,
Tools, Grounding** — light up as it plans, calls tools and retrieves knowledge.

- **Realms**: Government, Enterprise (financial, healthcare, telco, retail, logistics), SMB (including WAISentry,
  Wursta's 24/7 security operations), Agent Workforce (Wursta's AI staffing agency that delivers branded Word,
  PowerPoint and Excel files) — plus the internal Platform Core (Pantheon advisory suite and Agent Forge, the agent
  factory) and the Wursta Delivery Engine (WurstaBots, Atlas migration suite, innovation pipeline).
- **Compositions**: Pantheon strategy engagement, Atlas migration pipeline, Agent Forge build flow, WAISentry 24/7
  security operations, Agent Workforce job, Citizen Services Framework (proposed), real-estate enterprise sync
  (proposal), meeting-intelligence loop.
- **Security layers** (`security_layers` in `hive.yaml`, shown on the realm cards): Google Security Operations,
  Model Armor and Google Threat Intelligence around Government and Enterprise — a reference architecture, not enforced
  in this demo — and WAISentry around SMB, Agent Workforce and the internal realms (Platform Core, Wursta Delivery Engine).
- **Skill library**: the seven `wco-ge-skills`, reused by agents and exposed over MCP.

All organisations, people and records in this repository are **synthetic**.

## Two editions

| | Internal (Wursta) | Showcase (Google and clients) |
|---|---|---|
| Audience | Wursta staff, behind IAP | Anyone with a Google account (Gmail or Workspace), app-level Google sign-in |
| Grouping | Realms, incl. internal Platform Core and Delivery Engine | Customer segments only: Government, Enterprise, SMB, Professional Services, Agent Workforce |
| Content | Internal use cases | Client-framed overrides (`catalog/editions/showcase/agents*.yaml`), edition copies of fixtures, docs and KB docs |
| Language | English | English and Spanish (`catalog/editions/showcase/i18n/es*.yaml`) |
| Extras | — | Per-session, per-user and app-wide token limits, activity log, 1–5 rating after each demo, `/admin` |

`HIVE_EDITION=showcase` selects the edition for engines, the web app, the KB sync and the smoke test. Both editions share
the Vertex AI Search stores: every document is tagged with the editions that use it and agents filter on it. One-time
setup of the showcase site: `deploy/setup_showcase.sh` (session secret, service account, public Cloud Run service).

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
HIVE_GH_REPO=<owner>/<repo> deploy/setup_cicd.sh                # keyless GitHub Actions deploys (below)
```

### Auto-deploy

Every push to `main` runs the tests, then [`deploy.yml`](.github/workflows/deploy.yml) redeploys only what changed
([`deploy/changes.py`](deploy/changes.py)):

| Change | Redeploys |
|---|---|
| `web/`, `Dockerfile`, anything in `agenthive/` but the corpus | web app: image built in Actions, new Cloud Run revision (IAP and access untouched, then checked) |
| `catalog/realms/<realm>*.yaml` | that realm's engine |
| `tools/<module>.py` | engines of the realms whose agents use that module's tools |
| shared code (factory, router, models, grounding, fixtures, `hive.yaml`) | all five engines |
| `grounding/corpus/<realm>/` | that realm's Vertex AI Search data store |
| `deploy/seed/`, `grounding/bq/` | the BigQuery demo warehouse |
| `README.md`, `docs/`, `tests/` | nothing |

Engines deploy in parallel (one job per realm) and each is probed with one Flash-Lite turn before the job passes.
Run it by hand from the Actions tab with `targets` = `all`, `web`, `engines`, `kb`, `bq` or realm ids.
Auth is Workload Identity Federation: only `refs/heads/main` of this repository can impersonate the deployer, which
can roll out revisions, engines and demo data but cannot change IAM, IAP or any other Cloud Run service. Project values are repository
secrets (`GCP_PROJECT`, `GCP_WIF_PROVIDER`, `GCP_DEPLOYER_SA`), masked in the public logs; without them the deploy
jobs are skipped.

Try one agent locally through the same router:

```bash
GCLOUD_ACCESS_TOKEN=$(gcloud auth print-access-token) .venv/bin/python deploy/local_run.py proteus "ROI of a $180k project saving 6 FTE?"
```

## Adding an agent

Add a YAML entry and (optionally) tools — no glue code. See [docs/adding-agents.md](docs/adding-agents.md).
