# What Agent Workforce is and how a job works

Owner: Wursta Agent Workforce product team. Last reviewed 2026-11-01. Prototype documentation for the Wursta Agent Hive; customer names in the demo (Kitewing Software) are fictional.

## In one line

**Hire an AI expert. Get a finished, branded document. Pay per job.**

Agent Workforce is a virtual staffing agency powered by AI. Instead of hiring freelancers, a customer browses a marketplace of 70 specialist AI experts, submits a job brief in plain English, sees the cost upfront, and receives polished deliverables — Word, PowerPoint, Excel, PDF, CSV or Markdown — formatted to the company's brand guidelines. Think of Fiverr or Upwork, but the workers are AI agents.

## The customer journey

| Step | What happens |
|---|---|
| 1. Browse | 70 specialist agents across 10 departments (Marketing, Social Media, Sales, Operations, Writing, Strategy, AI Assistant, Customer Success, E-commerce and Media). |
| 2. Brief | Describe the job in plain English, like briefing a contractor: what you need, who it is for, the format and when. |
| 3. Estimate | See the cost upfront before committing — time and materials, by priority tier (Urgent, Standard, Economy). |
| 4. Execute | An orchestrator breaks the job into sub-tasks and assigns specialists, who collaborate. Every deliverable passes QA review and fact-checking. |
| 5. Deliver | Download the finished, brand-styled file (.docx, .pptx, .xlsx, .pdf, .csv or .md). Ask for revisions like you would with a contractor. |

## Core capabilities

- **Brand Intelligence** — upload brand guidelines, logo and templates. The system learns fonts, colours, tone of voice and writing style and applies them to every deliverable.
- **Multi-Agent Orchestration** — an orchestrator breaks complex work into sub-tasks, assigns specialists and synthesises one coherent deliverable.
- **Multi-Format Output** — Word, PowerPoint, Excel, PDF, CSV and Markdown.
- **AI-Powered Quality Assurance** — every deliverable passes a QA review agent and a fact-checking layer before it reaches the customer.
- **Revision Workflow** — request changes like with a real contractor; each revision is a new version of the file.

## What a good brief contains

1. The deliverable and format ("a client proposal as a Word document", "a 4-week LinkedIn calendar in Excel").
2. The audience (public, a named client, internal) and the goal.
3. The facts the specialist must use (prices, dates, proof points) — specialists never invent numbers.
4. Deadline or priority (urgent, standard, no rush).
5. Anything to avoid (names that may not appear, competitors, claims).

## What happens inside a job (the orchestrated flow)

1. **Scope** — the brief becomes a scoped job: deliverables, format, specialists, assumptions and a job id.
2. **Estimate** — the cost per priority tier is shown upfront (illustrative pricing in this prototype). In the demo the customer approves the recommended tier.
3. **Execute** — usually 1 to 3 specialists draft the content using the customer's brand profile and the department's deliverable template.
4. **QA & fact-check** — the QA agent checks the draft against the brief and the brand, verifies claims against the customer's approved facts and public sources, and returns a corrected version.
5. **Deliver** — Document Studio renders the corrected version into the branded file; the customer downloads it and can ask for revisions.

## In this hive

The Agent Workforce realm of the Wursta Agent Hive is a working prototype of the product: the orchestrator, the Marketplace Guide, Brief & Estimate, Brand Intelligence, QA & Fact-Check, Document Studio and six specialists (SEO Strategist, Social Media Planner, Proposal Writer, SOP Builder, Go-To-Market Strategist and Long-Form Writer). Files are rendered for real (.docx, .pptx, .xlsx, .md, .csv); PDF export runs in the product. The demo customer is Kitewing Software, a fictional field-service software company.
