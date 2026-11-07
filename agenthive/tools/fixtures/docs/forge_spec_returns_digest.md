# Agent spec — Returns Insight Digest (Ridgeline Outfitters)

**Spec version:** 1 · **Prepared by:** Forge Architect · **Approved by builder:** Marta Quintero · **Date:** 2026-11-06
*Fictional demo spec for the Forge Builder.*

## Goal

Every Monday, tell the merchandising lead which products are being returned most and why, so they can fix listings,
sizing charts or suppliers before the next buy.

## Users

Merchandising lead (reads the email on Monday), customer-service lead (reads the sheet).

## Inputs and outputs

- **Inputs:** Shopify orders and returns from the last 7 days (Shopify Admin connector).
- **Outputs:** (1) rows appended to the "Returns log" sheet: week, product, units sold, units returned, return rate,
  top reason; (2) a Gmail draft to the merchandising lead with the top 10 products by return rate, a one-line
  "what to check" per product and the change versus last week.

## Topology

Single agent (no sub-agents).

## Connectors

| Connector | Status | Why |
|---|---|---|
| shopify_admin (pin 1.4.x) | ready (official) | orders and returns |
| google_sheets | ready (official, signed-in user) | returns log |
| gmail | ready (official, signed-in user) | Monday draft |

## Tools

| Tool | Connector method | Purpose |
|---|---|---|
| list_returns(start_date: str, end_date: str) | shopify_admin.list_returns | returns with product and reason |
| return_rates(returns: list[dict], orders: list[dict], top_n: int) | none (pure function) | units sold, returned, rate; top N with at least 5 units sold |
| log_return_rows(rows: list[dict]) | google_sheets.append_rows | append to "Returns log" |
| draft_digest_email(to: str, subject: str, body: str) | gmail.create_draft | Monday draft (never sent by the agent) |

## Secrets (names only)

SHOPIFY_STORE_DOMAIN, SHOPIFY_ADMIN_TOKEN — read from the environment in the test pane and from Secret Manager in
production. Gmail and Sheets act as the signed-in user (OAuth); no secrets.

## Memory

Last week's top 10 (product ids and rates only) to show the change versus last week.

## Settings

Schedule Mondays 07:00 America/Denver; DRY_RUN=true in sandbox; minimum 5 units sold to rank a product.

## Test cases

1. return_rates computes units sold, returned and rate per product.
2. Products with fewer than 5 units sold are excluded from the ranking.
3. list_returns follows pagination to the last page.
4. log_return_rows appends one row per product with the declared columns.
5. draft_digest_email creates a draft and never sends.
6. Dates are computed in America/Denver.
7. No secret appears in logs or errors.

## Acceptance criteria

- The Monday draft lists at most 10 products, each with rate, top reason and change versus last week.
- The sheet gets one row per ranked product per week; re-running the same week does not duplicate rows.
- Nothing is sent or written outside the sheet and the draft.
