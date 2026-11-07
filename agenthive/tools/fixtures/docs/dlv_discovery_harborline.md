# Discovery notes — Harborline Logistics (fictional) · Workspace + Gemini

**Date:** 2026-11-03 · **Wursta:** Ana Lucia Mendoza (engagement lead), Priyanka Desai (solutions architect)
**Harborline:** Janet Okoro (COO, sponsor), Brian Castillo (IT Manager), Kim Albright (HR business partner), Lisa Moreau (VP Sales)

## Company snapshot
- Third-party logistics provider: HQ in Savannah plus 4 warehouses (3 US, 1 in Nuevo Laredo, Mexico).
- **850 employees** need accounts: ~575 office staff, ~160 warehouse frontline on shared devices, ~90 sales, 25 people in IT/HR/finance support functions are already counted above.
- Today: Exchange 2019 on-premises in hybrid with Microsoft 365 (about 60% of mailboxes already in Exchange Online), OneDrive barely used.
- **File shares: about 9 TB** on two Windows servers (operations, finance, customer contracts). Unknown number of PST files.
- Identity: an existing third-party identity provider will stay; Workspace must federate with it (1 SSO integration plus user provisioning).

## What they want
1. Move everyone to **Google Workspace Enterprise Standard**: mail, calendar, contacts, file shares to Shared drives.
2. **Gemini for Workspace pilot for 100 seats** (customer service, sales, finance) with prompting training and a usage review after 60 days.
3. **One AI agent** for customer service: answers "where is my shipment?" questions from the transport management system (TMS) API and drafts replies for agents to approve. Medium complexity; TMS has a documented REST API.
4. Change management and communications for all 850 users, Spanish material for the Nuevo Laredo warehouse.
5. Live training — Kim expects **about 12 live sessions** (end users, warehouse huddles, champions, admins).
6. **Four weeks of hypercare** after the last wave.

## Constraints and dates
- Peak-season freeze: **no changes between 2026-11-15 and 2027-01-08**.
- Kickoff target **2027-01-11**; all users migrated by **2027-04-30**.
- CFO wants a **fixed price** for the programme; budget "in the 300 to 350 thousand dollar range".
- DNS is managed by an external web agency — contact not confirmed yet.
- About 290 stale accounts in the directory need clean-up before provisioning (Harborline IT owns this).

## Assumptions discussed
- Harborline provides admin access to both tenants within a week of kickoff.
- Cutovers on Friday nights; warehouses need on-site floorwalkers on the Monday after their wave.
- The CRM Outlook add-in used by sales must have an answer before the sales wave (vendor offers a Gmail add-on).

## Explicitly not wanted / not now
- No migration of the 7-year-old journaling archive (stays with the current vendor until contract end).
- No mobile device management project — basic mobile management only.
- No data clean-up or de-duplication of the file shares.

## Open questions
- Exact PST footprint (Atlas pre-flight scan to run in January).
- Whether the TMS API rate limits allow the agent's expected 3,000 queries per day.
- Who signs off the AI agent's reply templates (customer service director?).
