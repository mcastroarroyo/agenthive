# Enterprise Sync Standards (Vulcan)

**Owner:** Data & Integration practice · **Last reviewed:** 2026-10-23 · **Status:** current
Synthetic demo document. Vulcan is a multi-tenant middleware that removes double data entry between CRMs
(HubSpot, Salesforce), construction-management (Procore) and BigQuery. Sablewood's Data & Integration practice runs it for
real-estate and construction clients whose teams re-key deals into project systems by hand.

## 1. Canonical model
Every tenant syncs into the same four entities:
- **Opportunity** — opportunity_id, name, amount_usd, stage, close_date, account_id, project_code, owner_ref,
  source_system, source_updated_at.
- **Account** — account_id, name, domain, industry, city.
- **Project** — project_code, name, stage, contract_value_usd, start_date, completion_date, site_address,
  source_updated_at.
- **ChangeOrder** — change_order_id, project_code, number, status, amount_usd, approved_at.
The **project code** (format PRJ-####) is the join key across systems. Records without a valid project code are
quarantined, not guessed.

## 2. Stage harmonisation
CRM stages map to prospect → qualified → contracting → won (or lost). Construction stages map to pre_construction →
construction → closeout → warranty. Stage maps are configured per tenant and versioned.

## 3. System of record (default rules)
| Data | Master |
|---|---|
| Company / account data | HubSpot (marketing-led CRM) |
| Opportunity stage | the most advanced CRM stage |
| Opportunity amount before contract | the most recently updated CRM |
| Amount after the deal is won | Procore contract value, including approved change orders |
| Project and change-order data | Procore |
| Project name | Procore when the project exists |

## 4. Conflict resolution
- Two CRMs disagree on stage: take the most advanced stage. If one says **lost** while another is active, send the
  record to **manual review** — never auto-resolve a lost deal.
- CRM amounts differ by more than **10%**: manual review.
- A source not updated for **90 days** is flagged **stale**; stale sources lose ties.
- Every resolved field records the winning system and the rule applied (field-level lineage).
- Resolved values are **written back** to the losing systems only for fields the tenant allows (amount, stage, name by
  default); write-backs are batched and logged.
- The manual-review queue has an SLA of 2 business days; the tenant's data steward owns it.

## 5. Architecture (per tenant)
- **Ingestion:** vendor webhooks where available, plus change-data-capture polling every 15 minutes for CRM objects and
  hourly for Procore; a nightly reconciliation job compares counts and checksums.
- **Processing:** Cloud Run services for mapping and conflict resolution; Pub/Sub between stages for retries and
  back-pressure; dead-letter topics for poison messages.
- **Storage:** BigQuery dataset per tenant with raw_* tables (as received) and canonical_* tables (resolved), partitioned
  by date and clustered by project code.
- **Secrets:** vendor OAuth tokens in Secret Manager, one secret per tenant and system, rotated on vendor schedule.
- **Isolation:** tenant id on every row and message; no cross-tenant queries; separate service identities per tenant.

## 6. API budget guardrails
Keep planned daily API usage below **50%** of each vendor limit configured for the tenant, leaving room for users and
other integrations. Initial loads run off-hours and page through results (100 records per read call). Alert at 70%.

## 7. Data quality checks
Row counts by object, null rates on key fields, project-code format, currency conversions, and drift between CRM amount
and Procore contract value. Failures block the canonical load for that object, not the whole tenant.

## 8. Onboarding a tenant
1. Connect systems with least-privilege service accounts in each vendor.
2. Profile objects and confirm the field mapping with the tenant (rows below 0.85 confidence need sign-off).
3. Dry-run the initial load and review conflicts.
4. Go live with read-only sync; enable write-backs after two clean weeks.

## 9. Status
In this demo the middleware simulates mapping, conflict resolution and sync plans over synthetic tenants; no
vendor APIs are called.
