# Pricing and packaging (price book effective 2026-07-01)

Owner: Lena Okafor (VP Sales) with Marcus Bell (COO & CFO). Synthetic demo document — Kitewing Software is fictional. All prices in USD.

## Plans

| Plan | Annual billing | Monthly billing | Technicians | Highlights |
|---|---|---|---|---|
| Starter | $39 per technician per month | $45 | 5-25 | Dispatch board, mobile app with offline mode, work orders with photos and signatures, basic invoicing, customer notifications, email support |
| Growth | $69 per technician per month | $79 | 10-250 | Everything in Starter + customer portal, maintenance agreements and recurring billing, parts & inventory, accounting connector, open API and webhooks, dashboards, chat and phone support (8x5) |
| Enterprise | $99 per technician per month | not offered | 50 minimum | Everything in Growth + SAML single sign-on and SCIM, multi-branch permissions, audit log, sandbox tenant, Insights included, 99.9% uptime SLA with credits, named CSM, 24x7 P1 support |

- Starter is capped at **25 technicians**; a customer that grows beyond 25 must move to Growth. Recurring maintenance agreements also require Growth.
- **Single sign-on (SAML) is an Enterprise feature.** All plans support multi-factor authentication.
- Quarterly invoicing is available for Growth and Enterprise when ACV is $50,000 or more, at no uplift.

## Add-ons

| Add-on | Price | Available on |
|---|---|---|
| Route Optimizer | $15 per technician per month | Growth, Enterprise |
| Kitewing Assist (AI copilot on Gemini) | $20 per technician per month | Growth, Enterprise |
| Insights (BigQuery analytics) | $600 per month flat | Growth (included in Enterprise) |

## Implementation services

| Package | Fee | Fits | Duration | Includes |
|---|---|---|---|---|
| QuickStart | $4,500 | Up to 25 technicians | 3 weeks | Remote configuration, 2 training sessions, CSV import of customers and equipment |
| Standard | $12,000 | Up to 150 technicians | 6-8 weeks | Guided configuration, train-the-trainer for dispatchers and technicians, accounting connector, go-live support |
| Premium | $28,000 | Over 150 technicians or Enterprise | 10-12 weeks | Dedicated implementation consultant, multi-branch design, SSO, 2 weeks of hypercare |

- **Data migration** from a legacy system: $3,500 per source system.
- **Onsite training:** $1,800 per day.

## Standard discounts (subscription only)

| Discount | Rule |
|---|---|
| Volume | 100-199 technicians: 5% · 200 or more: 10% |
| Multi-year | 2-year term: 3% · 3-year term: 6% (prices locked for the term) |
| Nonprofit | 10% for registered nonprofits |

Standard discounts stack multiplicatively, then any discretionary discount is applied on top.

## Discretionary discount approval matrix

| Discretionary discount | Approver |
|---|---|
| Up to 10% | Account Executive — no approval needed |
| 10.1% to 20% | VP Sales — Lena Okafor |
| 20.1% to 30% | Deal desk — Dana Whitfield (CEO) and Marcus Bell (COO & CFO) |
| Above 30% | Not allowed |

- The **total** subscription discount (all discounts combined) may never exceed **35%**.
- Implementation fees can be discounted up to 25% with VP Sales approval and are never waived entirely.
- Seasonal technician licences (pest control, landscaping, snow removal) always need deal desk approval.

## Worked example

140 technicians on Growth with Route Optimizer and Assist, annual billing, 1-year term:
list subscription 140 × ($69 + $15 + $20) × 12 = $174,720; volume discount 5% → **ACV $165,984** (effective $98.80 per technician per month). Standard implementation $12,000 + one data-migration source $3,500 = $15,500. **First-year total $181,484.** No approval needed.

## Terms

- Net 30 payment terms. Annual plans are invoiced upfront.
- Prices are locked for the contract term; renewal increases are capped at 5% per year.
- Renewal quotes go out 90 days before the renewal date.
- Always produce quotes with the quoting tool (or the Pre-Sales Lookup agent) — never calculate prices by hand in emails.

## Quick answers

- "Can we get SSO on Growth?" — No; SSO is Enterprise only (minimum 50 technicians).
- "Is Assist available on Starter?" — No; Assist and Route Optimizer need Growth or Enterprise.
- "Do you charge for office users?" — No; pricing is per field technician. Office and dispatch users are free.
- "Is there a free trial?" — A 14-day guided trial on a demo tenant, booked through the account executive.
