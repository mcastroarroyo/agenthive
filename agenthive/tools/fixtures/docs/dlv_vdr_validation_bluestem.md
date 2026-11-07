# Validation Report — Bluestem Foods analytics platform UAT (fictional)

## 1. Document control

| Field | Value |
|---|---|
| Version | 0.9 |
| Date | 2026-10-30 |
| Author | Sofia Brandt (Wursta) |
| Status | Final |
| Client | Bluestem Foods Co. |

## 2. Revision history

| Version | Date | Author | Change |
|---|---|---|---|
| 0.8 | 2026-10-27 | S. Brandt | First UAT cycle |
| 0.9 | 2026-10-30 | S. Brandt | Re-test of fixed defects |

## 3. Summary of results
User acceptance testing covered 14 test cases across the ERP, WMS and EDI pipelines and the first five dashboards. Overall pass rate: 95%. One critical defect remains open on the WMS pipeline and is expected to be fixed before go-live.

## 4. Test scope
12 test cases: pipeline loads and reconciliation for ERP orders, WMS inventory and retailer EDI; dashboard filters, freshness and row-level security. Marketing spend pipeline and the forecast model are out of this cycle.

## 5. Test environment and data
UAT dataset `bluestem_uat` with October data (31 days); production-like volumes; Looker Studio UAT workspace.

## 6. Test cases and results

| ID | Test case | Result | Defect |
|---|---|---|---|
| TC-01 | ERP orders daily load completes before 06:00 | Pass | |
| TC-02 | ERP orders reconcile to source totals (±0.1%) | Pass | |
| TC-03 | WMS inventory load completes | Pass | |
| TC-04 | WMS inventory reconciles to source on-hand units | Fail | DEF-031 |
| TC-05 | Retailer EDI files parsed for all 9 retailers | Pass | |
| TC-06 | EDI late-file detection raises an alert | Fail | |
| TC-07 | Sales dashboard filters by region and category | Pass | |
| TC-08 | Inventory dashboard region filter includes all regions | Pass | |
| TC-09 | Dashboards show data freshness timestamp | Pass | |
| TC-10 | Row-level security: regional manager sees own region only | Pass | |
| TC-11 | Executive dashboard KPIs match finance close | Pass | |
| TC-12 | Pipeline re-run is idempotent (no duplicates) | Pass | |

## 7. Defects

| ID | Severity | Description | Status |
|---|---|---|---|
| DEF-031 | Sev1 | WMS pipeline duplicates rows on retry, inflating on-hand units by up to 4% | Open |
| DEF-027 | Sev3 | Dashboard tooltip shows UTC instead of Central time | Closed |

## 8. Data validation evidence
Row counts and sums reconciled for ERP orders (31 of 31 days) and EDI (9 of 9 retailers). WMS on-hand units differ on 6 of 31 days (see DEF-031).

## 9. Recommendation (go / no-go)
**Recommendation:** GO for production cutover on 2026-11-09.

## 10. Sign-off

| Role | Name | Date | Decision |
|---|---|---|---|
| Wursta QA Lead | Sofia Brandt | 2026-10-30 | Approved |
| Wursta Delivery Lead | Grace Whitmore | | |
| Client Business Owner | Karen Voss | | |
