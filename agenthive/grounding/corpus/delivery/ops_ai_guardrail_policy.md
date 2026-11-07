# Model Armor & Outbound AI Guardrail Policy

**Owner:** AI Governance Lead · **Last reviewed:** 2026-10-20 · **Status:** current
**Control:** WC-AI-01 (generative AI usage and guardrails). Synthetic demo document.

## 1. Scope
Every outbound model call made by a Wursta agent — internal WurstaBots, Hive demo agents and partner-facing bots — passes
through the outbound guardrail before it reaches a model endpoint. Responses are screened on the way back. The goal is
simple: no personal data or secrets leave in a prompt, no injected instruction gets executed, and no runaway agent
burns budget unnoticed.

## 2. Layers
1. **Aegis pre-check** — a fast, deterministic scan (patterns and heuristics) for personal data, secrets, injection
   phrases and cost anomalies. It produces the verdict log used in audits.
2. **Model Armor** — the production control on the Vertex AI call path, configured with templates for prompt-injection
   and jailbreak detection, sensitive-data detection, malicious-URL detection and responsible-AI content filters.
3. **Sensitive Data Protection** — infoType-based de-identification for documents and free text before they are used
   in prompts, for categories that patterns cannot catch reliably (for example person names and addresses).
Aegis never replaces Model Armor; it adds deterministic evidence and cost controls on top.

## 3. Verdicts
| Verdict | When | What happens |
|---|---|---|
| **allow** | nothing found | the call proceeds |
| **allow_with_warning** | weak injection signals (score 0.2-0.59) | proceeds; logged for weekly review |
| **redact** | personal data found (email, phone, payment card, national id numbers, IBAN) | values are replaced with typed tokens such as [EMAIL_1] and the redacted prompt proceeds |
| **block** | any secret (API keys, private keys, credential assignments, service-account identities) or an injection score of 0.6 or higher | the call is stopped; the calling agent's owner is notified |

## 4. Personal data
- Detected categories are replaced with numbered tokens so the model can still reason about them ("the customer at
  [EMAIL_1]") without seeing the value. Re-identification, when needed, happens only in the calling application.
- Payment card numbers are validated with a checksum to avoid false positives.
- Prompts are stored only in redacted form; the verdict log keeps masked values (first two and last four characters).

## 5. Secrets
A secret in a prompt is treated as a potential leak even if the call is blocked: the owner **rotates the secret within
24 hours** and confirms in the incident ticket. Agents must load secrets from Secret Manager at runtime, never from
prompts, chat or configuration text.

## 6. Prompt injection
Injection usually arrives inside retrieved content — a partner document, an email, a web page — rather than from the
user. Signals include instructions to ignore previous instructions, requests to reveal the system prompt, role hijacks
("you are now…", "developer mode"), instructions to send data to a URL, bulk data requests and long encoded blobs.
Scores add up per signal; at 0.6 the call is blocked. **External callers** (partner bots, public channels) are always
treated as untrusted: their retrieved content is wrapped as data and never as instructions.

## 7. Cost anomalies
Each agent has an hourly baseline (calls, tokens, cost). An anomaly is raised when tokens or calls reach **3x the
baseline** in the current hour, or when an agent's spend reaches **USD 25 in an hour**. Response: throttle the agent to
2x its baseline, page the owner, and look for retry loops (repeated identical prompts are the most common cause).
Budgets per project are reviewed monthly by AI Governance.

## 8. Logging and retention
Verdict logs, masked findings and usage metrics are retained for 400 days (WC-LG-01) and reviewed weekly. Blocked calls
and secrets are reviewed within one business day.

## 9. Exceptions
Exceptions (for example a sanctioned red-team test) need written approval from the AI Governance Lead, a time limit
of at most 7 days and a named owner. Exceptions never cover real client personal data.

## 10. Roles
- **Agent owners** fix their agents' findings and rotate leaked secrets.
- **AI Governance** owns this policy, the Model Armor templates and the baselines.
- **Security** handles incidents raised from blocked calls.
