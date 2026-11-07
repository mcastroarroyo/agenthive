# Delivery modes, Gemini Enterprise and A2A

Owner: Wursta Agent Workforce product team. Last reviewed 2026-11-01. Prototype documentation for the Wursta Agent Hive.

Agent Workforce runs on Google Cloud and reaches customers in two ways. Both run on Wursta's infrastructure, so customers only ever see the outputs — the agents, prompts and orchestration stay protected (IP protection).

## Mode 1 — Standalone SaaS web app

- Browse the marketplace, submit jobs, track progress and download deliverables in a web app.
- Sign in with Google Sign-In.
- **Credit-based pay-per-job:** customers buy credits in advance (1 credit = $1) and each job reserves its estimate plus a buffer; the unused buffer is refunded when the job closes. Pricing is illustrative and not final.
- Best for: small and mid-size teams that want finished documents without any setup.

## Mode 2 — Gemini Enterprise Agent Marketplace

- The same specialist agents appear inside the customer's Gemini Enterprise, next to their other agents.
- Users brief them from Gemini Enterprise; deliverables come back as files.
- **Billing runs through the customer's Gemini Enterprise subscription.**
- Best for: organisations already standardised on Gemini Enterprise that want governed access to specialists in the tool their people already use.

## How the pieces talk: A2A

Agent Workforce uses the **Agent2Agent (A2A) protocol** so its agents can be discovered and called by other agent platforms — for example from Gemini Enterprise — while the work itself runs on Wursta's infrastructure. Customers call a specialist; they do not get its internals.

## File formats

| Format | Typical deliverables |
|---|---|
| Word (.docx) | Proposals, SOPs, SEO audits, briefs, whitepapers, press releases |
| PowerPoint (.pptx) | Pitch decks, go-to-market plans |
| Excel (.xlsx) | Content calendars, trackers, financial models |
| PDF | Any document, for sharing as final (exported in the product) |
| CSV | Data exports, calendar rows for scheduling tools |
| Markdown (.md) | Content for websites, wikis and repositories |

Every file carries the customer's brand: fonts, colours, wordmark, title page or title slide, header and footer, styled tables and frozen spreadsheet headers.

## Security and data

- Each customer's brand profile, approved facts and deliverables are kept per customer.
- Specialists use only the brief, the customer's brand profile and approved facts, connected data the customer chose to share (for example a website snapshot) and public sources for fact-checking.
- In this hive, all data is synthetic and every customer is fictional.
