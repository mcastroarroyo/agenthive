# Model Tier Policy — Flash-Lite, Flash and Argon

**Owner:** Tomás Herrera, AI Engineering Lead · **Last reviewed:** 2026-10-20 · **Status:** current
**Supersedes:** Model Selection Guide (Gemini 1.5 era).

## The rule

**Use the cheapest model tier that does the job.** Upgrade only with evidence from evaluations, never because a
bigger model "feels safer". Every agent and every step in a multi-agent pattern declares its tier and a one-line
reason in the catalog (`model` and `model_reason`).

## The three tiers

| Tier | Catalog value | Model family | Relative cost per token (illustrative) | Default for |
|---|---|---|---|---|
| Flash-Lite | `lite` | Gemini Flash-Lite | 1× | Routing, classification, extraction, notifications, templated drafting, knowledge-base Q&A, skills |
| Flash | `flash` | Gemini Flash | about 3× input / 6× output | Tool orchestration, analysis over data, multi-step reasoning — **the default** |
| Argon | `argon` | Gemini 4 Argon (deep reasoning tier) | about 20× input / 30× output | Deep planning and synthesis when that *is* the product |

The exact model versions behind each tier are pinned in the tier configuration, not in agent code. When the
configuration moves to a new model version, the evaluation sets are re-run before the change is released.

## When to use each tier

### Flash-Lite

Use it when the task is narrow and the answer is constrained:

- routing a request to the right agent or queue;
- classifying, tagging or extracting fields into a JSON schema;
- answering from retrieved documents where retrieval does the heavy lifting (for example the Context Librarian);
- drafting from a template, notifications, short summaries;
- every skill in the `wco-ge-skills` library (they call Flash-Lite with a response schema).

### Flash

Use it when the agent must choose and chain tools, reason over tool results or data, or write a structured analysis:

- multi-tool productivity agents (Workspace Pro, Brief Me);
- specialists that call deterministic tools and explain the results (Xenophon, Ariadne, Prometheus, Proteus);
- search-grounded research and synthesis;
- the synthesis step of a parallel pattern (Pantheon Rapid Assessment).

### Argon

Use it only when deep planning, adaptive decomposition or high-stakes trade-off reasoning *is the product*:

- **at most one or two agents per realm**, each with a written justification in `model_reason`;
- examples in the Hive: Hermes (adaptive coordination and cross-specialist synthesis) and Daedalus (architecture
  trade-offs);
- never for routing, extraction, formatting or anything a deterministic tool can compute.

## Design rules that keep cost down

1. **Push numbers into tools.** Dates, costs, scores, story points and ROI come from deterministic tools. A small
   model plus a good tool beats a large model doing arithmetic.
2. **Mix tiers inside patterns.** In sequential and parallel patterns, give each step its own tier — for example a
   Flash-Lite planner, a Flash researcher and a Flash writer.
3. **Retrieval before reasoning.** Improve grounding (better documents, ownership, freshness) before upgrading the
   model.
4. **Short instructions.** Long instructions cost tokens on every turn; move reference material into the knowledge
   base.
5. **Measure.** Track cost per conversation per agent monthly (Agent Deployment Checklist, section 7).

## Upgrade process

1. Build or extend the evaluation set with the failing cases.
2. Try instruction, tool-docstring and grounding fixes on the current tier first.
3. If the pass rate is still below target, run the evaluation on the next tier and record pass rate, latency and cost
   per conversation for both.
4. Upgrade only if the quality gain is material and the cost increase is acceptable to the business owner. Record the
   decision in `model_reason`.

Downgrades follow the same process in reverse and are encouraged: re-test Flash agents on Flash-Lite every quarter.

## Illustrative cost example

A knowledge-base answer with about 6,000 input tokens (instruction plus retrieved passages) and 400 output tokens
costs roughly 4 times more on Flash than on Flash-Lite, and about 22 times more on Argon. At 50,000 questions a month
that is roughly USD 38 on Flash-Lite, USD 140 on Flash and USD 840 on Argon for the same answer quality — and the gap
multiplies for agents that make several model calls per turn. Use the illustrative price sheet
(`estimate_gcp_monthly_cost`) for a first estimate and the official pricing calculator before quoting.

## Anti-patterns

- An Argon coordinator whose only job is routing — use Flash-Lite routing plus specialists.
- Upgrading the model to fix a vague tool docstring.
- Asking any model to compute a schedule or an ROI instead of calling the tool.
- One model for everything "for simplicity".

## Exceptions

Exceptions to this policy (for example a client contract that mandates a specific model) are approved by the AI
Engineering Lead and recorded in the agent's catalog entry.
