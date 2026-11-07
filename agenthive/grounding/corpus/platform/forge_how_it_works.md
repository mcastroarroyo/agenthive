# Agent Forge — How the Forge Works: Roles, Areas and the Build Flow

**Owner:** Elena Marsh, Forge Platform Owner · **Last reviewed:** 2026-11-02 · **Status:** current

## What Agent Forge is

Agent Forge is Wursta's internal factory for client-ready AI agents. **Agent Forge turns a plain-English request into
a tested, deployed AI agent wired to a client's real systems.** A Wursta builder describes the agent, picks the client
and the connectors; the forge plans, builds, tests and deploys it, and keeps every version and every run on record.
The forge is a web app on Cloud Run behind Google Identity-Aware Proxy (IAP).

## Why it exists

- **Every client runs a different stack.** Online stores on Shopify, finance on QuickBooks, auto shops on Tekmetric,
  facilities teams on Asset Panda, venture firms on Affinity — each needs an authenticated API client before an agent
  can do anything useful. The forge builds that client once as a reusable connector.
- **Requests arrive as loose descriptions.** "An agent that gets data from every employee on their bay times" must
  become a spec, tools and tests. The Plan stage does that and asks the builder when it is unsure.
- **The first version is rarely right.** Agents improve through plain-English feedback. One internal briefing agent
  went through eight versions after feedback on dates, links and tone — each one tested and recorded.
- **Deployment, secrets and access are hard to manage by hand.** The forge versions every agent, keeps secrets in
  the test pane (per session) and Secret Manager (production), and scopes what each person can see.

## Roles

| Role | Who | Can do |
|---|---|---|
| Admin | Wursta platform owners | Everything a builder can, plus users, roles and clients |
| Builder | Wursta consultants and engineers | Create, modify, test and deploy agents and connectors; see all clients |
| Demo | Prospects or client stakeholders | See and try only the agents of the clients they are assigned to |

Sign-in is through IAP with the person's Google account. Demo access is granted per person and per client, with an
expiry date; a demo user assigned to no client sees nothing.

## App areas

- **Home** — "What type of agent do you need?" A plain-English prompt starts an agent build or a connector build.
  Choose the client, attach connectors, click **Plan**.
- **Agents** — the catalog across clients: status (draft, building, ready, deployed), version, topology (single
  agent or workflow of sub-agents) and connectors.
- **Connectors** — reusable API clients any agent can attach. Official connectors ship with the template; custom
  connectors are researched and built by the forge from uploaded or linked documentation.
- **Jobs** — the durable log of every forge run: create, modify, fork, deploy, connector and connector_modify, with
  status. In-flight jobs survive a page reload.
- **Deployed** — agents running for clients.
- **Admin** — users, roles and client assignment.

## The build flow (6 stages + 1 loop)

1. **Describe** — the builder writes the request in plain English and picks the client and connectors.
2. **Plan** — the architect drafts the spec (goal, users, inputs and outputs, topology, connectors, tools, secrets,
   memory, tests, acceptance criteria) and asks the builder when it is unsure.
3. **Build** — the forge generates the agent and its tests, and builds any missing connector.
4. **Test** — the test pane runs the suite with session secrets; every test must pass.
5. **Deploy to sandbox** — versioned (v1, v2, v3…) and reviewed before release.
6. **Deploy to client** — live for the client; secrets in Google Secret Manager.

**Change requests loop back.** A change is written in plain English ("the LTV in the spreadsheet is always 0"); the
forge produces a new version, re-runs every test and redeploys. Every build, fix and deploy is recorded as a job.

Connectors follow the same path: describe the API or link its docs, the forge researches it and builds a reusable
client that every later agent can attach.

## Agent shapes

Most forge agents are **single agents** with function tools. Complex ones are **workflows of sub-agents** — for
example an order-support tracker runs an email searcher, then an order processor. Every agent gets per-session
secrets in the test pane, Secret Manager in production, memory across runs, and a test suite that must keep passing
on every change.

## Use-case groups (examples)

| Group | Example agents |
|---|---|
| Customer operations | Shopify Order Support Tracker (Gmail, Shopify, Sheets) |
| Field & shop operations | Employee Bay Time Tracker (Tekmetric); Asset Panda asset audits |
| Meeting & reporting automation | Weekly Status Recap Generator, Gmail Slides Maker, Board Deck Generator |
| Research & briefings | AI Video Briefing, Company Prospecting Assistant, Price Tracker, Flight Lookup |
| Creative production | Nano Banana Video Creator — concept images, storyboards, video |

## Value

- **Plain language in, deployed agent out** — and fixes are requested the same way.
- **Connectors compound** — a connector built for one agent serves every later agent and client.
- **Governed by default** — IAP, roles, client-scoped demo access, Secret Manager, version history, tests and the
  job log.
- **Safe iteration** — sandbox before client; tune-up jobs bring older agents up to current forge standards without
  changing their behaviour.
- **Demo-ready** — prospects see agents built for their own systems, scoped to their client only.

## Roadmap

- Redact secrets from job prompts and logs automatically.
- A client-facing usage view: runs, errors and cost per deployed agent.
- An official connector roadmap driven by client demand (for example HubSpot, Microsoft 365, NetSuite).
