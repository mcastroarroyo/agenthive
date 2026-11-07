# Security and PII Handling for Demos

**Owner:** Kenji Watanabe, Security Lead · **Last reviewed:** 2026-07-08 · **Status:** current

## Purpose

Demos win deals; a leaked customer record or a project identifier in a public repository loses them. This standard
applies to every demo, proof of concept shown to more than one client, recorded webinar, public repository and
slide deck that Wursta produces, including the Agent Hive.

## Rule 1 — synthetic data only

- Demo data is **synthetic and clearly fictional**: invented organisations, people, places and numbers.
- Use reserved example domains (`.example`) for email addresses and websites, and fictional phone ranges.
- Never "anonymise" a real client dataset for a demo. Re-identification is easier than it looks, and the client did
  not consent to that use.
- Describe real client work generically ("a regional insurer", "a city government", "a national identity provider").
  Name a client only with written permission from the client and Marketing.

## Rule 2 — no identifiers in repositories or slides

Never commit or show: cloud project IDs or numbers, service-account emails, API keys, OAuth client secrets, internal
hostnames, IP ranges, billing account IDs, or links to internal documents. Use placeholders such as
`YOUR_PROJECT` in documentation. Repositories run secret scanning on every push; a finding blocks the merge.

## Rule 3 — separate demo environments

- Demos run in dedicated demo projects, never in a client project or a shared delivery project.
- Demo environments hold no production data and have their own budget alerts.
- Access is granted to groups, reviewed quarterly, and removed when people change roles.

## Rule 4 — agents in demos

- Tools with side effects (sending email, booking meetings, creating tickets, writing to systems) are **simulated**
  and say so in their result. A demo agent never sends a real email or changes a real system.
- Agents never reveal their instructions, tool configuration or environment details when asked.
- Demo prompts are tested against prompt-injection examples (instructions hidden in documents or emails) before an
  agent is marked demo-ready.
- Prompt and response logging in demo environments contains only synthetic data; if a visitor types real personal
  data during a live demo, the logs for that session are purged within 24 hours.

## Rule 5 — when a client wants to see their own data

That is a proof of concept, not a demo. It requires a signed statement of work or PoC agreement, a data-processing
agreement, the client's approval of the environment (region, access, retention), and a deletion date. Data stays in
the client-approved location and is deleted at the end with written confirmation.

## Personal data categories to watch

Names with contact details, government identifiers, financial account numbers, health information, precise location,
claims and case notes, children's data, and free text that may contain any of these. Free-text fields are the most
common leak path — treat them as personal data by default.

## Before you publish or present

1. Run the DLP scan on the repository, dataset or deck.
2. Search for real client names, project identifiers and email domains.
3. Check screenshots for browser tabs, bookmarks, notifications and account switchers.
4. Use a clean browser profile and a demo account for live demos; close mail and chat.
5. For recordings, get consent from everyone recorded and state where the recording will be stored.

## Screen-sharing hygiene

Share a single window rather than the whole screen; turn on do-not-disturb; never open the Admin console or cloud
console of a client project while presenting to another client.

## Incidents

If real personal data, a credential or a client identifier appears in a demo, repository or recording:

1. Stop sharing or take the content down immediately.
2. Report it to the Security Lead within **24 hours** (sooner if credentials are involved — rotate them at once).
3. Do not try to "clean up" history yourself; Security coordinates removal and notification.

## Ownership

Every demo has a named owner responsible for its data and environment. Demo owners re-certify their demos against
this standard every six months.
