# Kitewing FieldOps product guide (November 2026)

Owner: Sofia Petrov, Product Manager. Synthetic demo document — Kitewing Software and its products are fictional.

## Capability matrix

| Capability | Starter | Growth | Enterprise |
|---|---|---|---|
| Scheduling and drag-and-drop dispatch board | Yes | Yes | Yes |
| Mobile app (iOS and Android) with offline mode, photos, signatures | Yes | Yes | Yes |
| Work orders, job checklists and custom forms | Basic forms | Yes | Yes |
| Inspection form templates (fire, electrical, elevator) | No | Yes | Yes |
| Customer notifications (SMS and email "on my way") | Yes | Yes | Yes |
| Basic invoicing | Yes | Yes | Yes |
| Maintenance agreements and recurring billing | No | Yes | Yes |
| Parts and inventory (van stock) | No | Yes | Yes |
| Customer portal (bookings, job status, invoices) | No | Yes | Yes |
| Accounting connector | No | Yes | Yes |
| Open API and webhooks | No | Yes | Yes |
| Standard dashboards | Basic | Yes | Yes |
| Multi-branch permissions | No | No | Yes |
| SAML single sign-on and SCIM provisioning | No | No | Yes |
| Audit log | No | No | Yes |
| Sandbox tenant | No | No | Yes |
| Insights (BigQuery analytics) | No | Add-on | Included |
| Route Optimizer | No | Add-on | Add-on |
| Kitewing Assist | No | Add-on | Add-on |

## Mobile app

- Works fully **offline**: technicians can open jobs, add photos, collect signatures and complete checklists without signal; everything syncs when the connection returns. Offline data is encrypted on the device and admins can sign a device out remotely.
- Supported: iOS 17 or later, Android 12 or later. Tablets supported.
- Known issue (November 2026): in rare cases photos taken offline in very low storage conditions fail to sync; a fix is scheduled for the 26.12 release.

## Kitewing Assist (AI copilot)

- Built on Google's **Gemini** models through Vertex AI, processed in US regions.
- Answers technicians' troubleshooting questions from equipment manuals, the customer's job history and the company's own knowledge articles, with the source shown.
- Writes job summaries and turns voice notes into work-order text.
- **Spanish-language answers:** beta for Growth and Enterprise customers from 2026-11-17; general availability targeted for February 2027.
- Customer data and prompts are **not used to train models**. Admins can enable or disable Assist per user group.
- Assist answers are evaluated weekly by Kitewing for accuracy; customers can flag a wrong answer from the app.

## Route Optimizer

- Builds each technician's route every morning from job windows, skills, parts and traffic, then **re-sequences live** when a job is cancelled or traffic changes (generally available since 2026-10-24).
- Drive-time reporting per technician and branch.

## Insights

- Analytics workspace on BigQuery with prebuilt dashboards (first-time fix, utilisation, drive time, revenue per technician, agreement renewals) and scheduled data export.
- Data refreshed nightly.

## Integrations

- **Accounting:** connector for the two most common small-business accounting packages (desktop and cloud), syncing invoices, payments and customers every 15 minutes. Other packages via CSV export or the API.
- **Google Workspace:** calendar sync for office users; sign in with Google on all plans.
- **Identity:** SAML 2.0 SSO and SCIM (Enterprise).
- **Open API and webhooks:** REST API with rate limits of 600 requests per minute per tenant (Growth and Enterprise).
- **Payments:** card payments through a PCI DSS Level 1 processor (hosted fields) — Kitewing never stores card numbers.
- **Data migration toolkit:** templates for spreadsheets and common legacy dispatch systems, including DispatchPro 7 exports.

## Limits

- Growth supports up to 250 technicians per tenant; larger operations use Enterprise.
- Up to 50,000 active maintenance agreements per tenant.
- File attachments up to 25 MB each.

## Roadmap (subject to change — do not commit dates to customers)

| Item | Target |
|---|---|
| Customer Portal 2.0 with online payments | December 2026 |
| Assist Spanish-language answers — general availability | February 2027 |
| Payroll integration | First half of 2027 |
| EU data hosting | 2027 |

Roadmap items are not available today. Sellers must say "on the roadmap, not available today" and never promise a date in writing without Sofia Petrov's approval.

## Support

| Plan | Channels | Hours | P1 first-response target |
|---|---|---|---|
| Starter | Email | Business hours | 30 minutes in business hours |
| Growth | Email, chat, phone | 8x5 | 30 minutes in business hours |
| Enterprise | Email, chat, phone, named CSM | 24x7 for P1 | 30 minutes, 24x7 |

First-response targets by priority: P1 30 minutes, P2 2 hours, P3 8 hours, P4 24 hours.
