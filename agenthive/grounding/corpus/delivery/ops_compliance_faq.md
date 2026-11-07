# Compliance FAQ — SOC 2 and ISO 27001 concepts

**Owner:** Security & Compliance (Data Protection Officer) · **Last reviewed:** 2026-10-01 · **Status:** current
Synthetic demo document. Written in our own words for the team; it explains concepts and our internal controls and is
not an audit opinion or a certification claim.

## What is SOC 2?
SOC 2 is an attestation report: an independent CPA firm examines a service organisation's controls against the Trust
Services Criteria. The criteria cover **security** (always in scope, often called the common criteria) and, optionally,
**availability**, **processing integrity**, **confidentiality** and **privacy**. The output is a report the
organisation shares with customers, usually under NDA. It is not a certificate and there is no "SOC 2 certified" logo.

## Type I vs Type II — what's the difference?
- **Type I** looks at the **design** of controls at a single point in time: are the right controls in place?
- **Type II** tests whether the controls **operated effectively over a period**, typically 3 to 12 months, using
  samples of evidence (tickets, logs, approvals).
Customers in regulated industries usually ask for Type II because it shows the controls actually work over time.

## What is ISO/IEC 27001?
An international standard for an **information security management system (ISMS)**. Unlike SOC 2, it is
**certifiable**: an accredited certification body audits the ISMS and issues a certificate. Key ideas:
- a risk assessment and risk-treatment plan owned by management;
- a **Statement of Applicability** listing which Annex A controls apply and why;
- Annex A of the 2022 edition contains 93 controls grouped into four themes — organisational, people, physical and
  technological;
- certificates last three years, with **surveillance audits every year** and a recertification audit at the end.

## "Aligned" vs "certified" — what can we say to clients?
In this demo, Wursta's programme is **aligned to** ISO/IEC 27001 and SOC 2 concepts, with a control set mapped to both.
Say: "Our security programme is aligned to ISO/IEC 27001 and SOC 2 concepts; we can share our control mapping and
complete your security questionnaire." Never say "certified" or "SOC 2 compliant" unless the certificate or report
exists and is current. RFP rows that require a certificate are marked **partial**, not met.

## Which internal controls answer the common questions?
| Question | Control | SOC 2 ref | ISO 27001 ref |
|---|---|---|---|
| Do you review access regularly? | WC-AC-01 Quarterly access reviews | CC6.1-CC6.3 | A.5.15, A.5.18 |
| Is MFA enforced? | WC-AC-02 MFA everywhere | CC6.1 | A.5.17, A.8.5 |
| How fast do you remove leavers? | WC-AC-03 Timely deprovisioning (sign-in suspended within 1 hour, client access within 4 hours) | CC6.2, CC6.3 | A.5.11, A.6.5, A.5.18 |
| How do you manage change? | WC-CM-01 Peer-reviewed changes | CC8.1 | A.8.32, A.8.25 |
| Incident response? | WC-IR-01 Triage within 1 hour; review within 10 business days | CC7.3-CC7.5 | A.5.24-A.5.26 |
| Vulnerabilities? | WC-VM-01 Critical fixed within 7 days, high within 30 | CC7.1 | A.8.8 |
| Data classification? | WC-DP-01 Public / Internal / Confidential / Client-Restricted | C1.1, C1.2 | A.5.12, A.5.13, A.8.12 |
| Vendors? | WC-VE-01 Questionnaire at onboarding and annually | CC9.2 | A.5.19, A.5.20 |
| Backups? | WC-BC-01 Daily backups; restore test twice a year | A1.2, A1.3 | A.8.13, A.5.30 |
| Training? | WC-HR-01 Security awareness in week 1 and annually | CC1.4, CC2.2 | A.6.3 |
| AI usage? | WC-AI-01 Approved AI tools; outbound guardrail | CC6.7, CC7.2 | A.5.10, A.8.11, A.8.12 |
| Logging? | WC-LG-01 Logs kept 400 days with alerting | CC7.2 | A.8.15, A.8.16 |
The mapping is illustrative and maintained by Security; the control catalogue is the source of truth.

## Can I paste client data into a public AI chatbot?
**No.** Client data is Confidential or Client-Restricted (WC-DP-01) and may only be processed in approved tools listed
by AI Governance (WC-AI-01). Wursta agents send model calls through the outbound guardrail (Aegis + Model Armor),
which redacts personal data and blocks secrets. Public consumer chatbots are not approved tools. If you already pasted
client data, report it to Security within 1 hour — it is handled as a potential incident (WC-IR-01).

## A client sent a security questionnaire — what now?
1. Check the answer library first (Security keeps approved answers).
2. Use control ids and evidence names from the catalogue; do not invent new commitments.
3. Evidence (policies, reports, screenshots) is shared only under NDA through a secure link, never by email attachment.
4. Anything that would create a new contractual commitment goes to Legal.

## Who do I ask?
Security & Compliance owns policies and the control catalogue; Legal owns contractual commitments; the Data Protection
Officer owns personal-data questions.
