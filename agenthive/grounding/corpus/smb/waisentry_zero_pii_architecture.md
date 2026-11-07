# WAISentry zero-PII architecture and the Alarm Panel Model

**Owner:** Wursta WAISentry team · **Source:** WAISentry brief ("Zero-PII data privacy") plus the Agent Hive demo design ·
**Last reviewed:** 2026-11-02 · Synthetic demo document; the client Kitewing Software is fictional.

## The promise
Personal data never leaves the client's environment. Telemetry is collected through native APIs and evaluated and
correlated **inside the client's own Google Cloud tenant**; before any alert is sent to the Wursta SOC, names, email
addresses, file names and message contents are replaced with tokens. Analysts work on tokens, signals and ATT&CK
techniques; only the client can turn a token back into a person.

## The Alarm Panel Model
A monitored home alarm sends the monitoring centre "zone 3 — back door opened at 02:05", and the centre acts on it
(calls the owner, dispatches help) without ever seeing inside the house. WAISentry works the same way: the SOC sees
"USR-CFA4 granted an unverified app mail scopes at 02:04 and a forwarding rule to EXT-CBE6 appeared at 02:05" and can
contain it, but the camera feed — who the person is, what the files and emails say — stays in the client's tenant.

## What is tokenised (demo design)
| Token | Replaces | Example |
|---|---|---|
| USR- | People and mailboxes (from the name or email) | USR-CFA4 |
| EXT- | External email addresses | EXT-CBE6 |
| FIL- | File names | FIL-48E5 |
| MSG- | Message subjects and bodies | MSG-92EF |
| DEV- | Personal device names (laptops are often named after people) | DEV-5259 |
| PHN- / ACC- | Phone numbers / bank or card account numbers | PHN-…, ACC-… |

**Kept in clear** because detection needs them and they are not personal data in this design: IP addresses and ASNs,
domains and URLs, app names and OAuth client ids, server names (MB-DC01 …), timestamps, scores and counts.

**Message bodies** are not sent at all: the in-tenant pipeline extracts signals first ("asks to change bank details",
"urgent", "quotes invoice TD-2026-1187", "discourages phone verification") and sends those instead of the text.

## How tokens are made
Token = HMAC-SHA256(tenant key, "type:value"), truncated to 4 hex characters per type. The same person always gets
the same token, so the SOC can correlate a login, an OAuth grant and a forwarding rule without knowing who it is. In
the service the tenant key stays in the client's tenant; **in this demo the key is a fixed constant** so results are
reproducible.

## Re-identification
- Only inside the client's tenant, by the client's administrator, with a reason (normally the incident id).
- Every re-identification is logged with an audit entry.
- The SOC side can never re-identify: requests from outside the tenant are refused.
- In the Agent Hive this is simulated with an explicit `in_tenant` flag on the tools.

## What leaves the tenant for a typical incident
For INC-1101-01 the payload sent to the SOC was about 2.3 KB: the incident id, the user token, the app name, client id
and scopes, the forward-to token, file tokens, message-subject tokens, IPs, ASN and geography, timestamps, ATT&CK
techniques and scores. Withheld: names and email addresses, file names and contents, subjects and bodies,
attachments, device names, phone and account numbers.
