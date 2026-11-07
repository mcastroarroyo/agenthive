# Workspace Migration Cutover Weekend Runbook

**Owner:** Laura Méndez, Workspace Practice Lead · **Last reviewed:** 2026-08-14 · **Status:** current
**Supersedes:** Exchange to Workspace Cutover Playbook (2023) — do not use the 2023 playbook.

## Purpose and scope

This runbook is Wursta's standard process for the cutover weekend of a migration from Microsoft Exchange (on
premises or online) or another mail platform to Google Workspace. It applies to every migration above 50 users.
Smaller tenants may compress the timeline, but they must keep the go/no-go meeting and the rollback criteria.

## What changed from the 2023 playbook

- The change freeze now starts **5 business days** before cutover (it was 48 hours).
- MX records switch on **Friday at 18:00 client local time** (it was Saturday 08:00), so the final delta pass gets a
  full night.
- DNS TTL is lowered to **300 seconds at least 72 hours** before cutover (it was 24 hours).
- Hypercare lasts **10 business days**, with floor-walkers on site on days 1–3 (it was 5 days, remote only).

When the 2023 playbook and this runbook disagree, this runbook is authoritative: it is newer, owned and approved.

## Roles

- **Cutover lead (Wursta)** — owns the timeline, chairs go/no-go and is the single voice on the bridge call.
- **Client IT lead** — owns DNS, firewall and identity changes; the only person who can approve a rollback.
- **Migration engineers** — run the migration tooling, monitor error reports and run the delta passes.
- **Change and communications lead** — sends user communications at every milestone.
- **Floor-walkers ("Wursta Guides")** — in-office and virtual help on Monday morning and through day 3.
- **Executive sponsor** — informed at go/no-go and at the end of Saturday validation.

## Timeline

### T-15 to T-5 business days — readiness

1. Users provisioned in Workspace through directory sync or the identity provider; licences assigned; 2-Step
   Verification enrolment at least 70% complete.
2. Pre-stage migration of mail, calendar and contacts older than 30 days complete, with item error rate below 0.5%.
3. Shared and resource mailboxes mapped (to Groups, delegated mailboxes or shared drives) and signed off by the
   client IT lead. **Recount them at T-15**: discovery undercounts them by 15–25% on almost every project.
4. Pilot group (5–10% of users, including at least one executive assistant) live for two weeks with no open
   severity-1 issues.
5. Communications sent: T-10 announcement, T-5 "what to expect", T-1 "what to do on Monday".
6. Litigation-hold and retention requirements mapped to Vault retention rules and holds, with Legal sign-off.

### T-5 — change freeze

No changes to mailbox permissions, distribution lists, transport rules or DNS other than the cutover plan.
Exceptions are approved by the cutover lead and logged.

### T-3 — DNS preparation

Lower the TTL of MX and autodiscover records to 300 seconds. Confirm SPF authorises Google's sending
infrastructure alongside the legacy platform; generate the DKIM key in the Admin console. DMARC stays at the client's
current policy until T+10.

### T-1 (Thursday) — go/no-go at 16:00 client time

Go criteria:

- Pre-stage complete for at least 98% of mailboxes.
- No open severity-1 defects from the pilot.
- Client IT lead and executive sponsor reachable on Friday evening and Saturday.
- Rollback plan reviewed and understood by both sides.

A "no-go" moves the cutover by **one week, never by one day** — a one-day slip burns the team and the users.

### Friday 18:00 — MX switch

1. The client IT lead switches MX records to Google; the cutover lead logs the timestamp.
2. Start the first delta pass immediately.
3. Check inbound flow every 30 minutes until 22:00 with test messages from three external domains.

### Saturday — final delta and validation

1. Second delta pass at 08:00 picks up messages delivered to the legacy platform during DNS propagation.
2. Validation script on 20 sample users, including executives and their delegates: mail, calendar, contacts,
   delegation, shared mailboxes and mobile sync.
3. Client IT lead signs off by 16:00. The executive sponsor receives a five-line status message.

### Sunday — hold point

No planned work; engineers on call. Legacy mailboxes are switched to read-only for users, never deleted.

### Monday (T+1) to T+10 — hypercare

- Floor-walkers on site 07:30–12:00 on days 1–3; a virtual help room is open all day.
- Daily 15-minute hypercare stand-up. Issues are triaged as S1 (cannot send or receive), S2 (feature broken for a
  group) or S3 (individual how-to).
- DMARC tightening and legacy licence removal happen only after T+10 and with client sign-off.

## Rollback

Rollback is possible until the Saturday 16:00 sign-off. Triggers: inbound mail failing for more than 2 hours
after the switch; more than 5% of validation users failing; or an identity outage. Rollback means pointing MX back to
the legacy platform and replaying messages that Google received during the window. The client IT lead decides; the
cutover lead recommends.

## Blackout periods

Do not schedule a cutover during the client's financial year-end close, a regulatory filing window or their peak
season. Record the blackout periods in the project plan at kickoff.

## Artefacts

Cutover plan (sheet), communications pack, validation script, go/no-go minutes, hypercare log and closure report.
Store them in the client delivery shared drive under "04 Cutover". The closure report feeds quality gate G6
(see Delivery Quality Gates).

## Lessons learned behind this runbook

- Executive assistants are the real launch customers: migrate them in the pilot and test delegation first.
- Saturday-morning MX switches left too little time for the final delta pass; Friday evening works better.
- PST files found on laptops after cutover are the most common source of "missing mail" tickets — inventory them
  during readiness and decide upfront whether they are imported.
