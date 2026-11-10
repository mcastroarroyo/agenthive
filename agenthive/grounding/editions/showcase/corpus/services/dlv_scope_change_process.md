# Scope Change and Change Order Process

**Owner:** PMO (Sablewood) · **Version:** 2.4 · **Last reviewed:** 2026-09-15 · **Status:** current
Synthetic demo document.

## 1. Why this matters
In FY26, 7% of delivery hours on fixed-price projects were spent on work nobody had agreed to pay for. Most of it
started as a "quick" request in a status meeting. The rule is simple: every request is logged, classified against
the signed SOW within three business days, and nothing outside scope starts before a signed change order.

## 2. Where scope creep shows up
- Status meetings and steering committees ("while you're at it", "can we also add", "one more thing").
- Email threads after a steering committee.
- Requests made directly to engineers on chat — engineers redirect them to the PM.
- Volume drift: more users, more terabytes, more dashboards than the SOW states.

The Scope Creep agent reads transcripts and emails, lists every ask, classifies it and drafts the change order.
Meeting-sentiment signals (frustration, disengagement, timeline pressure) are reported alongside, because the way we
answer matters as much as the answer.

## 3. Classification
| Class | Meaning | Action |
|---|---|---|
| In scope | Matches an in-scope item (IS-xx) of the signed SOW | Plan it; no paperwork |
| Out of scope | Matches an exclusion (OOS-xx) | Impact assessment and change order |
| Exceeds cap | In-scope type but beyond a contractual quantity (CAP-xx: users, TB, dashboards, sessions) | Change order for the extra units only |
| Ambiguous | Not covered by any clause | PM clarifies with the client; log in the change register |

Defects in accepted deliverables are not changes — they are handled under the 30-day warranty (CL-WAR-01).

## 4. Impact assessment (within 3 business days — clause CL-CHG-01)
Every assessment states: effort by role, price at the SOW's contracted rates, schedule impact in days, risks and
dependencies, and the effect on other deliverables. Use the reference effort recorded in the SOW's out-of-scope
catalogue when it exists; otherwise estimate with the estimation model.

## 5. Pricing a change order
- Contracted rates: the SOW's rate card minus its discount (for example, SOW-2026-0412 uses list rates minus 8%).
- Fixed-price SOWs: add a 10% contingency to the change order. T&M SOWs: the change order raises the not-to-exceed
  amount.
- Cap overages are priced per unit (per 100 users, per TB, per dashboard, per session) from the SOW's
  effort-per-unit table.

## 6. Approvals
| Change order total | Sablewood approver |
|---|---|
| Up to 10,000 USD | Delivery Lead |
| Up to 50,000 USD | Practice Director |
| Above 50,000 USD | VP Services |

The client signs every change order before work starts. Change orders are valid for 30 days. Informal approval by
email is not enough (amber clause LR-16 in the SOW Legal Playbook).

## 7. Talking to the client
- Thank the client for the request and confirm what is already covered, with dates.
- Present the change order as an option, not a penalty: what it adds, what it costs, when it can start.
- When the conversation shows frustration or timeline pressure, lead with the commitment that is at risk for the
  client (for example, a board date) and offer a 20-minute review call.
- Never start out-of-scope work "in goodwill" without the delivery director's written approval; goodwill work is
  logged with its hours.

## 8. Change register
Every request gets a line: id, date, requester, request text, classification, clause, decision, change-order id,
status. The register is reviewed in every steering committee. The weekly status report shows open change requests
older than five business days.

## 9. Examples (synthetic)
- Kestrel (SOW-2026-0412, fixed fee): public folders (OOS-01), PST ingestion (OOS-02), Teams chat history (OOS-03),
  150 contractors (CAP-01, priced per 100 users). Moving the executive wave earlier is in scope (IS-09) with 10
  business days' notice.
- Bluestem Foods (SOW-2026-0388, T&M): CRM source (OOS-01), real-time inventory (OOS-02), price recommendations
  (OOS-03), five-year backfill (OOS-04), three more dashboards (CAP-01), store-manager training (CAP-02). The
  late-EDI alert is in scope as a data-quality check (IS-04).
