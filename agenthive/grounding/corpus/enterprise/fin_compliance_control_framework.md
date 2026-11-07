# Quillmark Bank — Compliance Control Framework & Exam Readiness Guide

*Synthetic framework for the Wursta Agent Hive demo. Quillmark Bank and its supervisor are fictional; control
results are invented for demonstration.*

**Owner:** Chief Compliance Officer · **Reviewed:** 2026-10-15

## 1. How obligations map to controls

Every regulatory obligation in the compliance register is mapped to an internal policy and to one or more
controls. Each control has an owner, a frequency, a test procedure and an evidence standard. The mapping lives in
the GRC system and is the single source of truth for audits and supervisory examinations.

| Topic | Policy | Controls |
|---|---|---|
| AML transaction monitoring | Financial Crime Policy FCP-3 | CTL-AML-01 scenario run, CTL-AML-02 alert triage within 5 business days, CTL-AML-03 case decision and reporting within 30 days |
| Sanctions screening | Sanctions Policy SP-2 | CTL-SAN-01 wire screening coverage, CTL-SAN-02 potential-match disposition within 24 hours, CTL-SAN-03 list updates within 24 hours |
| KYC / customer due diligence | Customer Due Diligence Standard CDD-1 | CTL-KYC-01 risk-based periodic review (high 12 months, medium 24, low 36), CTL-KYC-02 beneficial-ownership verification |
| Wealth suitability | QPW-POL-07 | CTL-WM-01 annual profile review, CTL-WM-02 complex-product pre-approval, CTL-WM-03 record of advice |
| Complaints | Complaints Policy CP-1 | CTL-CMP-01 acknowledge in 5 business days, resolve in 30 days |
| Record keeping | Records Management Policy RM-2 | CTL-DR-01 retention of at least 5 years and retrieval within 48 hours |

## 2. Testing methodology

- Controls are tested quarterly by the second line using statistical or judgemental samples (minimum 25 items for
  per-event controls, all periods for periodic controls).
- **Pass rate** = (sample size − exceptions) / sample size.
- **Ratings:** Effective at 95% or more; Needs improvement at 85-94.9%; Deficient below 85% **or** when any
  critical exception is found (an exception that exposed a customer to harm or the bank to a regulatory breach).
- Every exception becomes an issue in the issues register with an owner, a root cause and a target date.

## 3. Evidence standards

Examiners and auditors expect evidence that is complete, dated and reproducible:

1. **Design evidence** — the policy section and the configuration (e.g. scenario thresholds export).
2. **Operating evidence** — a sample-test workpaper showing each sampled item, the expected outcome, the actual
   outcome and the tester's conclusion.
3. **Monitoring evidence** — dashboards or reports for the whole period (e.g. alert ageing by week).
4. **Governance evidence** — committee minutes showing issues were escalated and tracked.

A control without a sample-test workpaper is considered unevidenced. Screenshots must show the system date; extracts
must state the query or report parameters.

## 4. Q3 2026 open issues (summary)

| Issue | Control | Description | Owner | Target |
|---|---|---|---|---|
| ISS-2026-022 | CTL-KYC-01 | 214 overdue periodic reviews (3.1% of book), 19 of them high-risk customers | KYC Operations | 2026-12-31 |
| ISS-2026-029 | CTL-SAN-03 | List update of 2026-08-15 loaded after 41 hours (vendor feed outage) | Sanctions Compliance | Closed 2026-10-01 |
| ISS-2026-031 | CTL-AML-02 | 3 of 40 sampled alerts triaged late during the August fraud-ring surge | Financial Crime Ops | 2026-11-30 |
| ISS-2026-033 | CTL-CMP-01 | Card-fraud complaint surge in August breached the 30-day SLA for 4 sampled cases | Customer Care | 2026-11-30 |
| ISS-2026-035 | CTL-SAN-02 | 2 weekend potential matches cleared after 31 and 38 hours | Sanctions Compliance | 2026-12-15 |
| ISS-2026-038 | CTL-WM-01 | 4.8% of wealth suitability profiles older than 12 months | Private Wealth Supervision | 2026-12-31 |
| ISS-2026-040 | CTL-WM-02 | Critical: leveraged ETP held in a Conservative IRA via unsolicited order; private-credit interval fund sold to an ineligible client in 2025 | Private Wealth Supervision | 2026-12-15 |

KYC remediation contractors were engaged from July 2026 to clear ISS-2026-022 (Risk & Compliance professional fees
are above budget in Q3 2026 as a result).

## 5. Responding to a supervisory request

1. Log the request, the due date and the examiner-in-charge; assign one owner per numbered item.
2. Map each item to the topic, the controls and the evidence ids in the GRC vault; produce an index (item →
   evidence ids).
3. Disclose known exceptions and open issues proactively, with root cause, remediation and target dates. Never
   withhold an exception that the bank's own testing found.
4. Where evidence is missing, state why and when it will be available.
5. The Chief Compliance Officer signs off the response; Legal reviews any narrative statements.

## 6. Roles

- **First line** (business and operations) owns and operates controls.
- **Second line** (Compliance, Financial Crime) sets policy, tests controls and challenges.
- **Third line** (Internal Audit) independently audits the framework annually.
- Decisions on suspicious activity, sanctions blocks and regulatory filings are made by qualified officers only;
  AI assistants prepare analysis and drafts for their review.
