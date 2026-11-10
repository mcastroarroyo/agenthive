# Agent Forge — How the Forge Works: Roles, Areas and the Build Flow

**Owner:** Elena Marsh, Agent Forge Platform Owner (AI CoE) · **Last reviewed:** 2026-11-02 · **Status:** current

## What Agent Forge is

Agent Forge is the agent factory run by the AI Centre of Excellence (AI CoE) of Halvern Group, a diversified US
holding company, for its business units. **Agent Forge turns a plain-English request into a tested, deployed AI agent
wired to a business unit's real systems.** A business unit asks for an agent in plain English; an AI CoE builder
describes it, picks the business unit and the connectors; the forge plans, builds, tests and deploys it, and keeps
every version and every run on record. The forge is a web app on Cloud Run behind Google Identity-Aware Proxy (IAP).

| Business unit | Forge id | What it does | Time zone |
|---|---|---|---|
| Ridgeline Outfitters | `ridgeline_outfitters` | Outdoor-gear online retail (Shopify, QuickBooks, price feed, FleetBeam deliveries) | America/Denver |
| Copperline Auto Care | `copperline_auto` | Auto repair shops (Tekmetric) | America/Chicago |
| Summit Tire & Auto | `summit_tire` | Tire and auto service — acquisition pending close | America/Phoenix |
| Northpass Capital | `northpass_capital` | The group's venture-investment arm (Affinity CRM) | America/New_York |
| Stonebridge Facilities | `stonebridge_facilities` | Facilities management (Asset Panda) | America/Los_Angeles |
| Halvern Corporate | `halvern_corporate` | Group functions: IT, Finance, Marketing, travel and the AI CoE | America/New_York |

**Vocabulary note:** in the forge tools and records a business unit is called a "client" (for example the `client`
field of a spec, agent or job), and promotion to production is the deploy target `client`.

## Why it exists

- **Every business unit runs a different stack.** Ridgeline Outfitters sells on Shopify with finance on QuickBooks,
  Copperline Auto Care runs its shops on Tekmetric, Stonebridge Facilities tracks assets in Asset Panda and Northpass
  Capital manages deals in Affinity — each needs an authenticated API integration before an agent can do anything
  useful. The forge builds that integration once as a reusable connector.
- **Requests arrive as loose descriptions.** "An agent that gets data from every employee on their bay times" must
  become a spec, tools and tests. The Plan stage does that and asks the builder when it is unsure.
- **The first version is rarely right.** Agents improve through plain-English feedback. One Halvern Corporate
  briefing agent went through eight versions after feedback on dates, links and tone — each one tested and recorded.
- **Deployment, secrets and access are hard to manage by hand.** The forge versions every agent, keeps secrets in
  the test pane (per session) and Secret Manager (production), and scopes what each person can see.

## Roles

| Role | Who | Can do |
|---|---|---|
| Admin (`admin`) | AI CoE platform owners | Everything a builder can, plus users, roles and business units |
| Builder (`builder`) | AI CoE engineers and certified builders in Group IT | Create, modify, test and deploy agents and connectors; see all business units |
| Stakeholder (`stakeholder`) | Business-unit stakeholders | Preview and try only their own business unit's agents, in the sandbox |

Sign-in is through IAP with the person's Google account. Staff roles (admin, builder) are for Halvern employees on
halvern.example; business-unit stakeholders sign in with their business-unit domain (for example
ridgeline.halvern.example). Stakeholder access is granted per person and per business unit, with an expiry date; a
stakeholder assigned to no business unit sees nothing.

## App areas

- **Home** — "What type of agent do you need?" A plain-English prompt starts an agent build or a connector build.
  Choose the business unit, attach connectors, click **Plan**.
- **Agents** — the catalog across business units: status (draft, building, ready, deployed), version, topology
  (single agent or workflow of sub-agents) and connectors.
- **Connectors** — reusable API integrations any agent can attach. Official connectors ship with the template; custom
  connectors are researched and built by the forge from uploaded or linked documentation.
- **Jobs** — the durable log of every forge run: create, modify, fork, deploy, connector and connector_modify, with
  status. In-flight jobs survive a page reload.
- **Deployed** — agents running in production for business units.
- **Admin** — users, roles and business-unit assignment.

## The build flow (6 stages + 1 loop)

1. **Describe** — the builder writes the request in plain English and picks the business unit and connectors.
2. **Plan** — the architect drafts the spec (goal, users, inputs and outputs, topology, connectors, tools, secrets,
   memory, tests, acceptance criteria) and asks the builder when it is unsure.
3. **Build** — the forge generates the agent and its tests, and builds any missing connector.
4. **Test** — the test pane runs the suite with session secrets; every test must pass.
5. **Deploy to sandbox** — versioned (v1, v2, v3…) and reviewed before release; business-unit stakeholders preview
   and try it here.
6. **Deploy to production** — live for the business unit; secrets in Google Secret Manager.

**Change requests loop back.** A change is written in plain English ("the LTV in the spreadsheet is always 0"); the
forge produces a new version, re-runs every test and redeploys. Every build, fix and deploy is recorded as a job.

Connectors follow the same path: describe the API or link its docs, the forge researches it and builds a reusable
integration that every later agent can attach.

## Agent shapes

Most forge agents are **single agents** with function tools. Complex ones are **workflows of sub-agents** — for
example an order-support tracker runs an email searcher, then an order processor. Every agent gets per-session
secrets in the test pane, Secret Manager in production, memory across runs, and a test suite that must keep passing
on every change.

## Use-case groups (examples)

| Group | Example agents |
|---|---|
| Customer operations | Shopify Order Support Tracker (Ridgeline Outfitters: Gmail, Shopify, Sheets) |
| Field & shop operations | Employee Bay Time Tracker (Copperline Auto Care: Tekmetric); Asset Panda asset audits (Stonebridge Facilities) |
| Meeting & reporting automation | Weekly Status Recap Generator and Gmail Slides Maker (Halvern Corporate); Board Deck Generator (Northpass Capital) |
| Research & briefings | AI Video Briefing and Flight Lookup (Halvern Corporate); Company Prospecting Assistant (Northpass Capital); Price Tracker (Ridgeline Outfitters) |
| Creative production | Nano Banana Video Creator (Halvern Corporate Marketing) — concept images, storyboards, video |

## Value

- **Plain language in, deployed agent out** — and fixes are requested the same way.
- **Connectors compound** — a connector built for one agent serves every later agent and business unit.
- **Governed by default** — IAP, roles, business-unit-scoped stakeholder access, Secret Manager, version history,
  tests and the job log.
- **Safe iteration** — sandbox before production; tune-up jobs bring older agents up to current forge standards
  without changing their behaviour.
- **Business-unit preview** — stakeholders see and try agents built for their own systems in the sandbox, scoped to
  their own business unit only. Summit Tire & Auto, an acquisition pending close, stays in the sandbox until the deal
  closes.

## Roadmap

- Redact secrets from job prompts and logs automatically.
- A business-unit usage view: runs, errors and cost per deployed agent, for chargeback.
- An official connector roadmap driven by business-unit demand (for example HubSpot, Microsoft 365, NetSuite).
