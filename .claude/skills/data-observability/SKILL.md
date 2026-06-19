---
name: data-observability
description: Use when monitoring a data ingestion pipeline, checking data freshness, detecting sync failures, investigating missing or duplicate records, or implementing data quality checks on a BigQuery raw layer. Use when an Airbyte sync appears to succeed but data looks wrong, stale, or incomplete at the destination.
---

# Data Observability

## Overview

A sync that shows "success" in Airbyte is not the same as data arriving correctly. Observability requires verifying at the destination, not just the tool status. The four pillars to monitor: **freshness**, **volume**, **quality**, and **schema**.

See supporting files for detailed queries and patterns:
- [pipeline-health-checks.md](pipeline-health-checks.md) — freshness, row counts, sync gaps
- [data-quality-checks.md](data-quality-checks.md) — nulls, duplicates, schema drift
- [airbyte-monitoring.md](airbyte-monitoring.md) — logs, job status, Docker debugging

---

## The Four Pillars

| Pillar | Question | Symptom when broken |
|---|---|---|
| **Freshness** | Is data up to date? | `MAX(_airbyte_extracted_at)` is hours/days behind |
| **Volume** | Are the expected rows arriving? | Row count drops, tables not growing |
| **Quality** | Are values valid? | Unexpected nulls, type mismatches, out-of-range values |
| **Schema** | Did the source schema change? | New columns, missing columns, type changes |

---

## Daily Health Check — Minimum Viable Monitoring

Run this query every day (or schedule as a BigQuery scheduled query):

```sql
SELECT
  'orders'    AS table_name,
  COUNT(*)                                              AS total_rows,
  MAX(_airbyte_extracted_at)                            AS last_sync,
  TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(_airbyte_extracted_at), HOUR) AS hours_since_sync
FROM `project.postgres_raw.orders`

UNION ALL SELECT 'customers',   COUNT(*), MAX(_airbyte_extracted_at), TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(_airbyte_extracted_at), HOUR) FROM `project.postgres_raw.customers`
UNION ALL SELECT 'order_items', COUNT(*), MAX(_airbyte_extracted_at), TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(_airbyte_extracted_at), HOUR) FROM `project.postgres_raw.order_items`
UNION ALL SELECT 'products',    COUNT(*), MAX(_airbyte_extracted_at), TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(_airbyte_extracted_at), HOUR) FROM `project.postgres_raw.products`
UNION ALL SELECT 'payments',    COUNT(*), MAX(_airbyte_extracted_at), TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(_airbyte_extracted_at), HOUR) FROM `project.postgres_raw.payments`
UNION ALL SELECT 'suppliers',   COUNT(*), MAX(_airbyte_extracted_at), TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(_airbyte_extracted_at), HOUR) FROM `project.postgres_raw.suppliers`
UNION ALL SELECT 'reviews',     COUNT(*), MAX(_airbyte_extracted_at), TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(_airbyte_extracted_at), HOUR) FROM `project.postgres_raw.reviews`
UNION ALL SELECT 'geolocation', COUNT(*), MAX(_airbyte_extracted_at), TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), MAX(_airbyte_extracted_at), HOUR) FROM `project.postgres_raw.geolocation`

ORDER BY hours_since_sync DESC;
```

**Alert threshold:** `hours_since_sync > 2` for hourly syncs; `> 26` for daily syncs.

---

## Critical Non-Obvious Rules

- **Sync success ≠ data correctness** — always verify at destination, not just Airbyte UI status
- **Freshness and staleness are different problems** — a sync can run successfully but the *source* stopped writing (no new rows at origin)
- **Row count drops are harder to catch than spikes** — missing data has no signal unless you check
- **Schema changes are silent** — Airbyte may add a column without failing; downstream breaks without warning
- **Late-arriving data** — cursor-based syncs can miss rows written between the last watermark and sync start if the source has clock skew or async writes

---

## Common Observability Failures

| Symptom | Likely cause | Where to look |
|---|---|---|
| `hours_since_sync` keeps growing | Airbyte job failing silently | Airbyte job logs, Docker logs |
| Row count static for days | Source stopped writing, or cursor stuck | Source DB, Airbyte cursor state |
| Rows arrive but values wrong | Schema change at source | Compare source schema vs BigQuery schema |
| Duplicate rows on deduped table | PK not set correctly in Airbyte stream | Airbyte stream config, recheck PK column |
| Sync shows 0 rows processed | Watermark cursor too far ahead | Reset Airbyte connection state |
