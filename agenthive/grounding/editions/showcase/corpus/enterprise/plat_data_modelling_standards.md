# BigQuery Data Modelling Standards

**Owner:** Mateo Ruiz, Head of Data & Analytics · **Last reviewed:** 2026-04-10 · **Status:** current

## Purpose

Consistent, cost-efficient and governable BigQuery models across every programme and data product in the company.
Ariadne (the Pantheon data architect) applies these rules and checks its DDL with the `validate_ddl` tool before
handing it over.

## Layers and datasets

| Layer | Dataset name | Content | Who writes |
|---|---|---|---|
| Raw | `raw_<source>` | Source data as landed, append-only, with load metadata | Ingestion pipelines only |
| Staging | `stg_<domain>` | Typed, de-duplicated, conformed columns; one table per source entity | Transformation jobs |
| Marts | `mart_<domain>` | Star schemas for analytics and BI | Transformation jobs |
| Sandbox | `sbx_<team>` | Exploration; 30-day table expiration | Analysts |

Every dataset has a description, labels (`domain`, `owner`, `env`) and a location that matches the company's data
residency requirement for that data. Never mix regions within one model.

## Naming

- Everything in `lower_snake_case`. No spaces, no camelCase, no reserved words.
- Tables: `fct_` for facts, `dim_` for dimensions, `brg_` for bridge tables, `agg_` for aggregates, `stg_` for
  staging tables.
- Keys: `<entity>_id` for the natural or source key, `<entity>_sk` for surrogate keys.
- Booleans start with `is_` or `has_`. Timestamps end with `_ts` and are stored in **UTC**; local dates end with
  `_date`. Money ends with `_amount` and is `NUMERIC`, with a separate currency column when more than one currency
  exists.
- Avoid abbreviations unless they are the business's own language (for example `sku`, `fnol`).

## Star-schema rules

1. **State the grain** of every fact table in its description, in one sentence: "one row per claim payment".
2. Facts hold measures and foreign keys; descriptive attributes live in dimensions.
3. Use conformed dimensions across marts: `dim_date`, `dim_customer`, `dim_product`, `dim_location`, `dim_employee`.
4. Slowly changing dimensions: type 2 with `valid_from_ts`, `valid_to_ts` and `is_current` when history matters
   (customer segment, adjuster team); type 1 otherwise.
5. Degenerate dimensions (invoice number, claim number) stay in the fact table.
6. Prefer nested and repeated fields only for true one-to-few child data that is always read with the parent
   (for example the lines of a small order); otherwise model a separate fact.

## Partitioning and clustering

- **Every fact table is partitioned**, normally by the event date (`PARTITION BY DATE(event_ts)` or by a date
  column). Snapshot facts partition by snapshot date.
- Set `require_partition_filter = TRUE` on facts larger than about 100 GB.
- **Cluster** facts by up to four columns that are commonly filtered or joined, most selective first (for example
  `store_id, sku`).
- Large dimensions (over 1 GB) may be clustered by their natural key.
- Use partition expiration only for raw and sandbox data, never for marts without a retention decision.

## Keys and constraints

BigQuery does not enforce keys, but declare them so the optimiser and the catalog can use them:
`PRIMARY KEY (...) NOT ENFORCED` on dimensions and `FOREIGN KEY (...) REFERENCES dim_x(...) NOT ENFORCED` on facts.
**Create dimensions before the facts that reference them** — deployment scripts are ordered by dependency, and
`validate_ddl` reports a reference to a table that is created later as an error.

## Descriptions and catalog

Every table and every column has `OPTIONS(description = ...)`. The description of a fact states its grain; the
description of a measure states its unit and how it is calculated. Descriptions flow to the data catalog and are
what business users and agents search.

## Example

```sql
CREATE TABLE mart_claims.dim_policy (
  policy_sk STRING NOT NULL OPTIONS(description = "Surrogate key: hash of policy_id and policy_version"),
  policy_id STRING OPTIONS(description = "Policy number from policy administration"),
  product_code STRING,
  state_code STRING,
  PRIMARY KEY (policy_sk) NOT ENFORCED
) OPTIONS(description = "One row per policy version");

CREATE TABLE mart_claims.fct_claim_payment (
  payment_id STRING NOT NULL,
  claim_number STRING OPTIONS(description = "Degenerate dimension"),
  policy_sk STRING,
  payment_date DATE,
  payment_amount NUMERIC OPTIONS(description = "Payment in USD"),
  FOREIGN KEY (policy_sk) REFERENCES mart_claims.dim_policy(policy_sk) NOT ENFORCED
)
PARTITION BY payment_date
CLUSTER BY policy_sk, claim_number
OPTIONS(description = "One row per claim payment");
```

## Data quality

Each mart has automated checks: uniqueness of primary keys, not-null on keys and measures, referential integrity of
facts to dimensions, accepted values for codes, and freshness against the agreed load schedule. Failures alert the
dataset owner. Known source issues (for example duplicate parties or missing geocodes) are documented in the model
README with the chosen treatment.

## Personal data

- Keep personal data in a small number of restricted dimensions, protected with policy tags and column-level
  security; facts carry surrogate keys only.
- Free-text fields that may contain personal data (notes, descriptions) are not loaded into marts without a
  de-identification step.
- Analysts work on masked views by default.

## Cost hygiene

No `SELECT *` in scheduled queries or dashboards; use materialised views or aggregates for heavy dashboards; set a
maximum-bytes-billed limit on service accounts used by BI tools and agents.
