---
name: bigquery-engineering
description: Use when designing BigQuery datasets, choosing partition and clustering strategies, configuring IAM for service accounts, optimizing query costs, or setting up a raw ingestion layer. Use when troubleshooting expensive queries, partition pruning failures, or access denied errors in BigQuery.
---

# BigQuery Engineering

## Overview

BigQuery bills by bytes scanned. Every design decision — partitioning, clustering, column types, query patterns — affects cost and performance. The raw layer is append-heavy and must be designed to survive high-frequency syncs without runaway costs.

See supporting files for detailed guidance:
- [partitioning-and-clustering.md](partitioning-and-clustering.md)
- [cost-optimization.md](cost-optimization.md)
- [iam-setup.md](iam-setup.md)

---

## Dataset Structure

```
project/
  postgres_raw/        ← Airbyte destination; exact replica of source
  supply_chain_mart/   ← Future: dbt-transformed tables (not in current scope)
```

**Naming convention for raw tables:**

```
postgres_raw.orders
postgres_raw.customers
postgres_raw.order_items
```

Airbyte writes `_airbyte_*` metadata columns on every row — keep them. They are the audit trail and sync watermark.

---

## Partition & Clustering — Quick Decision

```
Table > 1 GB or will grow large?
├── NO  → No partition needed
└── YES → Queries filter by date range?
          ├── YES → Partition by DATE(_airbyte_extracted_at)
          └── NO  → Partition by cursor field (e.g., DATE(updated_at))

After partitioning — add clustering?
├── Deduped table (has PK)?     → CLUSTER BY id
├── Queries filter by FK?       → CLUSTER BY order_id (or most common FK)
└── Multiple access patterns?   → CLUSTER BY id, created_at (max 4 columns)
```

See [partitioning-and-clustering.md](partitioning-and-clustering.md) for gotchas and DDL templates.

---

## Raw Layer Table Template

```sql
CREATE TABLE IF NOT EXISTS `project.postgres_raw.orders`
(
  id              INT64,
  customer_id     INT64,
  status          STRING,
  total_amount    NUMERIC,
  created_at      TIMESTAMP,
  updated_at      TIMESTAMP,
  _airbyte_raw_id          STRING    NOT NULL,
  _airbyte_extracted_at    TIMESTAMP NOT NULL,
  _airbyte_normalized_at   TIMESTAMP,
  _airbyte_meta            JSON
)
PARTITION BY DATE(_airbyte_extracted_at)
CLUSTER BY id
OPTIONS (require_partition_filter = FALSE);
```

---

## Critical Non-Obvious Rules

- **Never use `localhost`** in any connection string — use service names or Cloud SQL proxy
- **Partition pruning requires direct filter on partition column** — `WHERE DATE(ts) = '2024-01-01'` works; `WHERE EXTRACT(YEAR FROM ts) = 2024` does NOT prune
- **`SELECT *` scans all columns** — no column pushdown on base tables; select only needed columns
- **Streaming inserts cost ~10x batch loads** — Airbyte batch load via GCS staging is always preferred
- **`INFORMATION_SCHEMA` queries are billed** — cache results or query infrequently

---

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `Access Denied: BigQuery` | Service account missing role | Add `BigQuery Data Editor` + `BigQuery Job User` |
| `Partition filter required` | `require_partition_filter = TRUE` | Add `WHERE _airbyte_extracted_at >= ...` |
| Query scans entire table | Partition column not used in WHERE | Filter directly on partition column, not derived expression |
| `Quota exceeded` | Too many concurrent jobs | Stagger sync schedules; check slot usage |
| GCS staging `Access Denied` | SA missing GCS write role | Add `Storage Object Creator` on staging bucket |
