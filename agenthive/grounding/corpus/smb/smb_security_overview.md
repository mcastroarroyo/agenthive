# Security, privacy and compliance overview

Owner: Noah Kim (IT & Security Administrator). Presales contact: Rosa Delgado (Sales Engineer). Last reviewed 2026-09-15. Synthetic demo document — Kitewing Software is fictional.

This overview summarises the approved answers used in security questionnaires. Quote the approved wording; if a question is not covered, escalate to Rosa Delgado rather than improvising.

## Hosting and data residency

- Kitewing FieldOps runs on **Google Cloud in US regions**, with backups in a second US region.
- **EU hosting is on the 2027 roadmap and is not available today.**
- Kitewing Assist uses Google's Gemini models through Vertex AI, also processed in US regions.

## Encryption

- **At rest:** all customer data is encrypted with AES-256. Database and backup keys are managed in Cloud KMS and rotated annually. Customer-managed keys are not offered.
- **In transit:** TLS 1.2 or higher (TLS 1.3 preferred) with HSTS; the mobile app pins the API certificate.
- **On devices:** offline data in the mobile app is stored encrypted; admins can sign a device out remotely.

## Identity and access

- **Customer access:** multi-factor authentication on every plan (authenticator app or security key), enforceable by admins. **SAML 2.0 single sign-on and SCIM provisioning are included in Enterprise.**
- **Kitewing staff access:** production access is limited to four named engineers through just-in-time elevation with MFA and full audit logging. Every employee uses hardware security keys, passes a background check and completes annual security training.
- **Least privilege** applies to every system; access is reviewed quarterly (the Q3 2026 review was completed on 2026-10-16).

## Certifications and testing

- **SOC 2 Type II** report covering Security, Availability and Confidentiality for October 2025 – September 2026. The 2026 renewal audit is in progress (fieldwork December 2026, report expected 2027-01-15). The report is shared under NDA.
- ISO 27001 is **not** held.
- An independent **penetration test** runs annually (last in May 2026; no critical or high findings open). Automated vulnerability scanning runs weekly; critical issues are patched within 7 days and high within 30 days.
- No public bug-bounty programme; responsible disclosure goes to the security contact on the website.

## Availability and recovery

- **Uptime:** Enterprise includes a 99.9% monthly uptime SLA with service credits. Starter and Growth target 99.9% without credits. A public status page reports incidents.
- **Backups:** point-in-time recovery with daily full backups kept 35 days.
- **Targets:** RPO 15 minutes, RTO 4 hours. Disaster-recovery restores are tested twice a year.

## Incident response

- A documented incident-response plan is tested annually.
- Customers are notified of a confirmed personal-data breach **without undue delay and within 72 hours**.
- Support priorities: P1 first response within 30 minutes (24x7 for Enterprise).

## Privacy

- Kitewing signs a standard **Data Processing Addendum (DPA)**. Kitewing is the processor; the customer is the controller.
- Data-subject requests are supported through admin export and deletion tools.
- **Subprocessors:** Google Cloud (hosting and AI models), a transactional email provider and an SMS gateway. The list is in the DPA annex; customers get 30 days' notice of changes.
- **Retention and deletion:** data is retained for the contract term. After termination customers can export for 30 days; data is then deleted within 60 days and backups age out within 35 days.

## AI (Kitewing Assist)

- Customer data and prompts are **not used to train models**.
- Processing stays in US regions and is covered by the same DPA.
- Admins can disable Assist per user group; answers show their sources and can be flagged by technicians.
- Kitewing evaluates Assist answer quality weekly.

## Payments

- Card payments are handled by a PCI DSS Level 1 payment processor through hosted fields. Kitewing never stores or processes full card numbers.

## Secure development

- Every change is peer-reviewed and passes automated tests and dependency scanning before deployment.
- Engineers complete secure-coding training (OWASP Top 10) within 14 days of joining and annually.
- Threat modelling is part of the design review for new features; a pen test is booked at least 3 weeks before major releases (for example Customer Portal 2.0).

## Documents available on request

| Document | Condition |
|---|---|
| SOC 2 Type II report | Under NDA |
| Penetration test executive summary | Under NDA |
| DPA and subprocessor list | Public on request |
| Completed standard security questionnaire | Through the account executive |
| Business continuity summary | Under NDA |

## Questionnaire process

1. The account executive sends the questionnaire to Rosa Delgado with the due date.
2. Rosa answers from the approved answer bank (the Pre-Sales Lookup agent uses the same bank).
3. Any question without an approved answer goes to Noah Kim; answers are added to the bank after approval.
4. Typical turnaround: 3 business days for up to 100 questions.
