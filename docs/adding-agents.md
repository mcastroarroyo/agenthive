# Adding agents to the Hive

Every agent is **data + tools**: a catalog entry (YAML) and the function tools it calls. The factory
(`agenthive/agents/factory.py`) turns the entry into an ADK agent; the realm's `HiveRouter` hosts it on Agent Engine;
the Hive UI renders it. No per-agent Python glue is needed.

## Files you touch

| What | Where |
|---|---|
| Catalog entries | `agenthive/catalog/realms/<realm>.yaml` or `<realm>__<part>.yaml` |
| Function tools | `agenthive/tools/<module>.py` (one module per realm or part) |
| Synthetic data for tools | `agenthive/tools/fixtures/<prefix>_<name>.json` → `fixture("<prefix>_<name>")` |
| Sample input documents | `agenthive/tools/fixtures/docs/<prefix>_<key>.md` (first line `# Title`) |
| Knowledge base (Vertex AI Search) | `agenthive/grounding/corpus/<realm>/<prefix>_<slug>.md` |
| BigQuery tables (optional) | schema `agenthive/grounding/bq/<module>.json` + rows `deploy/seed/bq_<module>.py` |

## Catalog entry (see `realms/platform.yaml` for complete examples)

```yaml
- id: wealth_sentinel          # lowercase snake_case, globally unique
  code: Wms                    # 3-char hex label, globally unique
  name: Wealth Sentinel
  cluster: financial           # must exist in hive.yaml for the realm
  industry: FINANCIAL          # optional small label on the hex
  status: demo_ready           # demo_ready | built | in_build | library
  tagline: one line, starts with what it does
  description: 2-4 sentences
  persona: who uses it
  use_cases: [3 bullets]
  model: flash                 # lite | flash | argon (cheapest tier that does the job)
  model_reason: why this tier
  pattern: single              # single | sequential | parallel | coordinator | loop  (+ steps)
  tools: [tool_a, tool_b]      # names from the tool registry
  grounding: [kb, fixtures:portfolio book]   # kb | google_search | bigquery:t1,t2 | fixtures:<what>
  instruction: |               # numbered working method — the factory adds identity, tools, grounding, guardrails
  output: what the answer looks like
  samples: [3 one-click prompts that work with the fixtures/docs]
  sample_doc: optional doc key offered as one-click input
  related: [other agent ids]
  kpis: [business metrics]
```

Multi-agent patterns use `steps` (each: `id, name, model, role, instruction, tools, grounding, output_key`, or
`agent_ref` to reuse another catalog agent). Later steps read earlier outputs with `{{output_key}}` placeholders.
`loop`: the last step is the critic and automatically gets `exit_loop`. The agent's own `instruction` is used for the
final/synthesis step (sequential, parallel, loop) or the coordinator (coordinator).

**Never** use single-brace `{word}` in instructions (reserved by ADK templating); use `{{state_key}}` only for step outputs.

## Model tier policy

- `lite` (Flash-Lite): routing, classification, extraction, notifications, templated drafting, KB Q&A.
- `flash` (default): tool orchestration, analysis over data, multi-step reasoning.
- `argon` (Gemini 4 Argon): only when deep planning/synthesis *is the product*; at most 1–2 per realm, justify it.

## Tool conventions

- Plain functions, every parameter type-hinted (`str, int, float, bool, list[str], list[dict]`), defaults where
  sensible, Google-style docstring — **the docstring is what the model sees**.
- Register with `@hive_tool("<module>")`; use `kind="action"` for simulated side effects (return `simulated=True`).
- Return `ok(...)` / `err(...)` from `_base`; never raise on bad input; deterministic; stdlib only; no network calls
  (use `llm_json` only if a model call is the point of the tool, and keep it on `lite`).
- Tool names are global: make them specific (`fin_portfolio_exposure`, not `get_data`).

## Data and naming rules (public repository)

- Everything is synthetic and clearly fictional: invented organisations, people and places; no real clients.
- Never write GCP project IDs, numbers or service-account emails in the repo.
- Client work is described generically (e.g. "national identity provider", "agriculture ministry",
  "real-estate developer").

## Check your work

```bash
HIVE_OFFLINE=1 .venv/bin/python -m pytest -q tests
```
