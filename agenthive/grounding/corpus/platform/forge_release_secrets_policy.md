# Agent Forge Release, Access and Secrets Policy

**Owner:** Kofi Mensah, Forge Admin · **Last reviewed:** 2026-10-30 · **Status:** current

## Versions

Every build and every change produces a new version (v1, v2, v3…). Versions are immutable: a fix is always a new
version. The version history keeps the plain-English request behind each version, the tests it passed, who built it,
who reviewed it and when it reached the sandbox and the client.

## Release path

1. **Test pane** — the full suite runs with session secrets. Release gate: every test passes; blocked tests count as
   failures.
2. **Sandbox** — the version is deployed to the sandbox for review. In sandbox `DRY_RUN=true`: emails become drafts
   and writes to client systems are simulated.
3. **Client** — promotion requires (a) the passing suite, (b) the version reviewed in the sandbox, (c) approval by an
   active admin or builder who did **not** build that version (four-eyes), and (d) every secret the agent needs
   present in the client's Secret Manager. **Prospects** stay in the sandbox until they sign.
4. **Rollback** — the previous client version stays available; rolling back is a deploy of that version.

Release notes describe what changed in the client's own words, the tests that passed and how to roll back.

## Access

- The forge sits behind Google Identity-Aware Proxy; there is no public access.
- Roles: **Admin** (users, roles, clients), **Builder** (create, modify, test, deploy), **Demo** (view and try the
  agents of assigned clients only).
- Demo assignments have an expiry date and are reviewed monthly. A demo user must never see another organisation's
  agents unless that client's owner approved it in writing.
- Staff roles (admin, builder) are for Wursta staff. External contractors need a named sponsor and an expiry date.
- Builders inactive for more than 60 days lose the role. Access reviews run quarterly.

## Secrets

- **Test pane:** builders enter secret values for their session only; nothing is persisted to the agent.
- **Production:** values live in Google Secret Manager under the client's scope; agents read them by reference at
  run time. The forge shows references, never values.
- Values never go into prompts, specs, code, tests, chat or logs. If one is pasted, the job prompt and log are
  redacted and the key is rotated — redaction hides the value, rotation makes the leaked value useless.
- Service-account key files are not used; agents run with their runtime identity.

## Redaction

Job prompts, build logs and specs pass through secret redaction before they are stored or shared. Detectors cover
common formats: Google API keys and OAuth client secrets, OpenAI-style `sk-` keys, Stripe-style keys, GitHub and
Slack tokens, Slack webhooks, AWS access keys and secret keys, Shopify tokens, JWTs, bearer tokens, private key
blocks, passwords embedded in URLs and generic `password=` / `api_key=` / `token=` assignments. Findings show the
type, line and a masked preview only.

## Jobs

Every create, modify, fork, deploy, connector and connector_modify run is a job with a status (queued, running,
waiting for input, succeeded, failed, cancelled). Jobs waiting for a builder's answer for more than 24 hours are
reviewed in the weekly forge stand-up.
