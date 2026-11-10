# Agent Forge Release, Access and Secrets Policy

**Owner:** Kofi Mensah, Forge Admin (AI CoE) · **Last reviewed:** 2026-10-30 · **Status:** current

## Versions

Every build and every change produces a new version (v1, v2, v3…). Versions are immutable: a fix is always a new
version. The version history keeps the plain-English request behind each version, the tests it passed, who built it,
who reviewed it and when it reached the sandbox and production.

## Release path

1. **Test pane** — the full suite runs with session secrets. Release gate: every test passes; blocked tests count as
   failures.
2. **Sandbox** — the version is deployed to the sandbox for review, and business-unit stakeholders preview and try it
   there. In sandbox `DRY_RUN=true`: emails become drafts and writes to business-unit systems are simulated.
3. **Production** — promotion requires (a) the passing suite, (b) the version reviewed in the sandbox, (c) approval
   by an active admin or builder on halvern.example who did **not** build that version (four-eyes), and (d) every
   secret the agent needs present in the business unit's Secret Manager. **Summit Tire & Auto** is an acquisition
   pending close: its agents stay in the sandbox until the deal closes.
4. **Rollback** — the previous production version stays available; rolling back is a deploy of that version.

Release notes describe what changed in the business unit's own words, the tests that passed and how to roll back.

## Access

- The forge sits behind Google Identity-Aware Proxy; there is no public access.
- Roles: **Admin** (`admin`: users, roles, business units), **Builder** (`builder`: create, modify, test, deploy),
  **Stakeholder** (`stakeholder`: preview and try, in the sandbox, the agents of their own business unit only).
- Stakeholder assignments have an expiry date and are reviewed monthly. A stakeholder must never see another business
  unit's agents unless that business unit's owner approved it in writing.
- **Information barrier:** Northpass Capital, the group's venture-investment arm, is behind an information barrier —
  its people must not see other business units' agents without written approval.
- Staff roles (admin, builder) are for Halvern employees on halvern.example. Business-unit stakeholders sign in with
  their business-unit domain (for example ridgeline.halvern.example). External contractors need a named sponsor and
  an expiry date.
- Builders inactive for more than 60 days lose the role. Access reviews run quarterly.

## Secrets

- **Test pane:** builders enter secret values for their session only; nothing is persisted to the agent.
- **Production:** values live in Google Secret Manager under the business unit's scope; agents read them by
  reference at run time. The forge shows references, never values.
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
