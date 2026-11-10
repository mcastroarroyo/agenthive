# Workspace Security Baseline and Data Regions Guidance

**Owner:** vacant (previous owner moved teams in May 2026 — reassignment pending) · **Last reviewed:** 2026-03-03
**Status:** ownerless — use with care

> Google Workspace features, edition entitlements and Admin console menus change frequently. Treat this document as
> Group IT's checklist and rationale, and **verify every setting and edition requirement against current Google
> documentation** (support.google.com and the Workspace Updates blog) before applying or recommending it.

## Purpose

The minimum security configuration Group IT applies to the company's Google Workspace, and to business units and
acquired companies as they join it, plus Group IT's guidance on data regions for teams with data residency
requirements.

## 1. Administrative accounts

- Separate admin accounts from day-to-day user accounts; admins do not read mail with their admin identity.
- Keep the number of super administrators small (two to four) and use delegated admin roles for everything else.
- Enforce security keys (phishing-resistant 2-Step Verification) for all admin accounts.
- Keep a documented break-glass super admin with credentials stored offline, reviewed quarterly.

## 2. User authentication

- Enforce 2-Step Verification for all users after an enrolment grace period (typically two weeks).
- Prefer passkeys or security keys for high-risk groups (executives, finance, admins).
- Where the company or a joining business unit uses a separate identity provider, configure SSO and decide
  explicitly where MFA is enforced.
- Set session lengths appropriate to the risk of each organisational unit.

## 3. Access and devices

- Context-aware access for sensitive apps and groups where the edition supports it (verify the edition).
- Mobile management: at least basic management for all devices; advanced management (screen lock, encryption,
  remote wipe) for devices that access sensitive data.
- Block or restrict access from unmanaged devices for high-risk organisational units.

## 4. Third-party apps

- Restrict third-party OAuth app access: unconfigured apps cannot access sensitive scopes; trusted apps are
  allow-listed after review.
- Review connected apps quarterly; remove those that are unused.

## 5. Sharing and data protection

- Drive external sharing: allowed only to allow-listed domains for sensitive units; warn users when sharing outside the
  organisation; disable "anyone with the link" by default for sensitive units.
- DLP rules for Drive, Gmail and Chat covering the company's sensitive data types (for example policy numbers,
  national identifiers, payment card numbers) — start in audit mode, then enforce.
- Classification labels where the edition supports them.
- Retention rules and legal holds in Vault aligned to the company's records policy (verify edition).

## 6. Gmail

- SPF, DKIM and DMARC configured; DMARC moved from monitoring to enforcement after the migration stabilises.
- Enhanced pre-delivery scanning and attachment protections enabled; external-sender warnings on.
- Compliance and routing rules documented and owned.

## 7. Logging and monitoring

- Alert centre notifications routed to a monitored group, not an individual.
- Audit and investigation reviews scheduled monthly.
- Where the edition supports it, export Workspace logs to BigQuery for retention and correlation with other security
  data.

## 8. Gemini features

Review the current Google documentation on how Gemini in Workspace handles customer data, which controls are
available per edition, and which settings admins can toggle per organisational unit. Communicate the position to
the company's privacy officer before enabling features broadly.

## Data regions guidance

### What data regions do

Data regions let an administrator choose where certain covered data at rest is stored — for example in the United
States or in Europe — for selected users or organisational units. Coverage applies to specific services and data
types, and some data (for example certain indexes, backups or processing) may be handled differently.
**Check Google's current documentation for the exact list of covered services and exclusions.**

### Editions

Data regions are available only in certain editions (historically enterprise-level and some education editions).
Group IT recommends confirming the current edition matrix before choosing or changing an edition; this is often the
deciding factor between two editions.

### How Group IT configures it

1. Agree the requirement in writing with the privacy or compliance officer: which users, which data, which region,
   and whether "no preference" is acceptable for anyone.
2. Map the requirement to organisational units or configuration groups.
3. In the Admin console, open the data regions setting (it has historically been under Data → Compliance; menus move,
   so search the console for "data regions").
4. Apply the policy to the chosen units and record the change in the configuration log.
5. Allow time for existing data to move; verify with Google's reporting and document the result for the privacy or
   compliance officer.

### When data regions are not enough

For stricter requirements, Group IT recommends discussing client-side encryption (the company holds the keys) and any
assured or sovereign controls offerings available for the company's jurisdiction — again, verify the current
offerings and editions.

## Review checklist for go-live

Super admins counted; 2SV enforced; OAuth restrictions in place; external sharing defaults set; DLP in audit or
enforcement mode; SPF/DKIM/DMARC verified; data regions configured if required; alert routing tested.
