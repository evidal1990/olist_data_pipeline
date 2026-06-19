# Raw Layer Design — Reference

## Principles

The raw layer is an exact replica of the source. No business logic, no transformations, no column removal. Future layers (dbt, etc.) handle interpretation.

---

## Naming Convention

```
<project>.<source>_raw.<connector>__<table>

Examples:
  supply_chain.postgres_raw.postgres__orders
  supply_chain.postgres_raw.postgres__customers
  supply_chain.postgres_raw.postgres__order_items
```

Use double underscore (`__`) to separate connector prefix from table name — consistent with Airbyte's naming output.

---

## Partitioning

| Table size | Partition by | Reason |
|---|---|---|
| > 1 GB | `DATE(_airbyte_extracted_at)` | Prune by ingestion date; cheap for monitoring queries |
| Query-heavy on date range | Cursor field (e.g., `DATE(updated_at)`) | Faster downstream reads |
| < 1 GB | No partition needed | Overhead not justified |

Airbyte writes a `_airbyte_extracted_at` timestamp on every row — always available as partition candidate.

---

## Clustering

```sql
-- Deduped tables: cluster by PK for point lookups
CLUSTER BY id

-- Event/append tables: cluster by most common filter
CLUSTER BY order_id   -- if downstream always filters by order

-- Large tables with multiple access patterns
CLUSTER BY id, created_at
```

Clustering is free at write time and reduces bytes scanned on reads. Max 4 columns.

---

## BigQuery Table DDL Template

```sql
CREATE TABLE IF NOT EXISTS `project.postgres_raw.postgres__orders`
(
  -- Source columns (mirror source schema exactly)
  id              INT64,
  customer_id     INT64,
  status          STRING,
  total_amount    NUMERIC,
  created_at      TIMESTAMP,
  updated_at      TIMESTAMP,

  -- Airbyte metadata (always keep)
  _airbyte_raw_id         STRING,
  _airbyte_extracted_at   TIMESTAMP,
  _airbyte_normalized_at  TIMESTAMP,
  _airbyte_meta           JSON
)
PARTITION BY DATE(_airbyte_extracted_at)
CLUSTER BY id
OPTIONS (
  require_partition_filter = FALSE
);
```

---

## Observability at Raw Layer

```sql
-- Daily row count by sync run
SELECT
  DATE(_airbyte_extracted_at) AS sync_date,
  COUNT(*)                    AS rows_loaded
FROM `project.postgres_raw.postgres__orders`
GROUP BY 1
ORDER BY 1 DESC;

-- Detect sync gaps (no data for a day)
SELECT
  DATE(_airbyte_extracted_at) AS sync_date,
  COUNT(*)                    AS rows
FROM `project.postgres_raw.postgres__orders`
WHERE _airbyte_extracted_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
GROUP BY 1
ORDER BY 1;

-- Latest sync watermark per table
SELECT
  'orders'    AS table_name, MAX(_airbyte_extracted_at) AS last_sync FROM `project.postgres_raw.postgres__orders`
UNION ALL
SELECT
  'customers' AS table_name, MAX(_airbyte_extracted_at) AS last_sync FROM `project.postgres_raw.postgres__customers`;
```

---

## What NOT to do at Raw Layer

- Do not rename columns
- Do not cast types
- Do not filter rows
- Do not join tables
- Do not drop `_airbyte_*` metadata columns
- Do not apply business rules

All of the above belong in the transformation layer (dbt).
