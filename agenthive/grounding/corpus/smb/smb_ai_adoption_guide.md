# AI adoption guide and AI use policy (draft v0.3)

Owner: Victor Lindgren (CTO) with Noah Kim (IT & Security) and Erin Walsh (People & Culture). Status: **DRAFT — pending leadership approval (target December 2026).** Until approved, the rules below apply as interim guidance and questions go to Noah Kim. Synthetic demo document — Kitewing Software is fictional.

## Why this guide exists

Kitewing wants to grow ARR 30% in 2027 with at most eight net new hires. AI should take on repetitive work in sales, support, finance and engineering — safely, measurably and without customer data leaking into unapproved tools.

## Approved tools

| Tool | Who | Approved for |
|---|---|---|
| Gemini in Google Workspace (Gmail, Docs, Sheets, Meet, Chat) | Everyone | Drafting, summarising, meeting notes, analysis of internal and customer data |
| Kitewing Assist (internal tenant) | Customer Success, Support, Product | Product knowledge and troubleshooting answers |
| Gemini Code Assist | Engineering | Code completion, review and test generation on Kitewing repositories |
| Agents built on Google Cloud (Vertex AI / Agent Engine) | Approved projects only | Workflows reviewed by Victor Lindgren and Noah Kim |

Any other AI tool (browser extensions, free chatbots, personal accounts) may only be used with **public** information.

## Data classes

| Class | Examples | Allowed in approved AI tools | Allowed in other AI tools |
|---|---|---|---|
| Public | Website, published case studies, press releases | Yes | Yes |
| Internal | Plans, internal metrics, project documents | Yes | No |
| Confidential | Pricing exceptions, HR files, financials, security reports | Yes, with care; never in prompts shared outside your team | No |
| Customer data | Customer records, jobs, tickets, invoices | Yes | **Never** |

Never paste passwords, API keys, card numbers or security reports into any prompt.

## Human review

- Anything an AI drafts that reaches a customer, a candidate or the public (emails, proposals, social posts, support replies) is **reviewed by a person before it is sent**.
- AI must never make decisions about hiring, pay, performance or credit on its own. In HR, AI may summarise and organise; people decide.
- Label AI-generated analysis as such when you share it, and keep the numbers traceable to their source.

## Maturity model

We assess AI readiness on six dimensions (12 questions, scored 1-5): **strategy & leadership** (weight 20), **data foundations** (20), **tools & infrastructure** (15), **skills & literacy** (15), **governance & risk** (15) and **culture & change** (15). The weighted average gives a level:

| Level | Name | Score | What it looks like |
|---|---|---|---|
| 1 | Exploring | 1.0-1.7 | Curiosity and individual experiments |
| 2 | Experimenting | 1.8-2.5 | Pockets of use with approved tools; no policy, metrics or owner |
| 3 | Formalising | 2.6-3.3 | Policy, owner and first measured use cases |
| 4 | Scaling | 3.4-4.1 | Several use cases in production with KPIs and training |
| 5 | Transforming | 4.2-5.0 | Processes redesigned around AI; continuous evaluation |

Kitewing's October 2026 leadership survey placed the company at the border of Experimenting and Formalising, with governance (no written policy yet), strategy (no AI budget) and skills (most teams untrained) as the weakest dimensions.

## Prioritising use cases

Score every candidate use case 1-5 on **value**, **effort** and **data readiness**:

- Priority score = 2 × value + data readiness − 1.5 × effort.
- **Quick win:** value 4-5 and effort 1-2. **Strategic bet:** value 4-5 and effort 3-5. **Fill-in:** value 1-3 and effort 1-2. **Deprioritise:** value 1-3 and effort 3-5.
- Data readiness below 3 means "fix the data first" before building.
- At most **three launches in the first 30 days** — adoption beats volume.

## The 90-day roadmap template

| Wave | Focus | Typical items |
|---|---|---|
| Days 0-30 | Foundations and quick wins | Approve this policy; 90-minute "AI at work" session for everyone; up to 3 quick wins with KPIs |
| Days 31-60 | Scale what works | Fill-ins, prompt libraries per department, data-quality owner for CRM |
| Days 61-90 | First strategic bet | Discovery and pilot of one strategic bet (for example churn-risk early warning on BigQuery) |

Every roadmap item has an owner, a KPI and a success measure agreed before work starts.

## Candidate use cases at Kitewing (shortlist)

- Sales: discovery-call prep and recap emails; security questionnaire first drafts.
- Customer Success: support ticket triage and suggested replies; churn-risk early warning from usage and tickets.
- Finance: personalised invoice-chasing emails; cash-flow forecast.
- Product & Engineering: release notes from pull requests; code review assistance.
- People: AI onboarding companion for new hires.
- Marketing: social content drafts from company news (with the brand check).

## Training

- Everyone completes **"AI at work — safe use of Gemini in Google Workspace"** within 30 days of joining (existing staff by 2026-12-31).
- Builders (2-3 people) follow a deeper track: prompt design, evaluation and agent patterns on Google Cloud.

## Measuring

Track per use case: hours saved per month, adoption (weekly active users), quality (error or override rate) and the business KPI it targets. Review monthly in the leadership meeting.
