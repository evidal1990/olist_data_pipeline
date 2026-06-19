# Partitioning & Clustering — Reference

## Partitioning

Partitioning splits a table into segments by a date or range column. BigQuery skips entire partitions that don't match the WHERE clause — this is partition pruning.

### Partition Types

| Type | Column | Use when |
|---|---|---|
| Ingestion-time | `_PARTITIONTIME` (auto) | No reliable date column; simplest setup |
| Column (timestamp) | `DATE(ts_column)` | Query by business date or sync date |
| Integer range | `RANGE_BUCKET(int_col, ...)` | Partitioning by ID range (rare in raw layer) |

**Recommended for Airbyte raw tables:** partition by `DATE(_airbyte_extracted_at)`.

This lets you:
- Monitor sync health by day with cheap queries
- Prune old partitions easily
- Keep partition count manageable (1 partition/day)

### Partition Pruning — Gotchas

Pruning only works when the WHERE clause references the partition column **directly**:

```sql
-- ✅ Prunes correctly
WHERE DATE(_airbyte_extracted_at) = '2024-06-01'
WHERE _airbyte_extracted_at >= '2024-06-01'
WHERE _airbyte_extracted_at BETWEEN '2024-06-01' AND '2024-06-30'

-- ❌ Does NOT prune — full table scan
WHERE EXTRACT(MONTH FROM _airbyte_extracted_at) = 6
WHERE FORMAT_DATE('%Y-%m', DATE(_airbyte_extracted_at)) = '2024-06'
WHERE DATE_DIFF(CURRENT_DATE(), DATE(_airbyte_extracted_at), DAY) < 30
```

### Partition Expiration

Set expiration to auto-delete old raw partitions and control storage costs:

```sql
ALTER TABLE `project.postgres_raw.orders`
SET OPTIONS (partition_expiration_days = 365);
```

For raw tables, 365 days is a safe default. Adjust based on retention policy.

### require_partition_filter

Forces every query to include a partition filter — prevents accidental full scans:

```sql
ALTER TABLE `project.postgres_raw.orders`
SET OPTIONS (require_partition_filter = TRUE);
```

**Recommended for large tables (> 10 GB).** Leave FALSE during development and initial load.

---

## Clustering

Clustering sorts data within each partition by the specified columns. BigQuery skips blocks that don't match the filter — this is called block pruning.

### Key Properties

- Free at write time (no extra storage cost)
- Improves read performance for high-cardinality filter columns
- Max 4 clustering columns
- Column order matters: put the most selective filter first
- Automatically maintained by BigQuery as data grows

### Clustering Column Selection

| Table type | Primary filter pattern | Recommended clustering |
|---|---|---|
| Deduped entity (orders, customers) | `WHERE id = ?` | `CLUSTER BY id` |
| Event / append-only (order_items) | `WHERE order_id = ?` | `CLUSTER BY order_id` |
| Time-series with multiple filters | `WHERE customer_id = ? AND status = ?` | `CLUSTER BY customer_id, status` |

### Supply Chain Raw Layer Reference

```sql
-- orders: Deduped, queried by id and customer_id
PARTITION BY DATE(_airbyte_extracted_at)
CLUSTER BY id, customer_id

-- order_items: Append-only, queried by order_id
PARTITION BY DATE(_airbyte_extracted_at)
CLUSTER BY order_id

-- customers: Deduped, queried by id
PARTITION BY DATE(_airbyte_extracted_at)
CLUSTER BY id

-- products: Deduped, sometimes filtered by category
PARTITION BY DATE(_airbyte_extracted_at)
CLUSTER BY id

-- payments: Deduped, queried by order_id
PARTITION BY DATE(_airbyte_extracted_at)
CLUSTER BY order_id, id

-- geolocation: Small reference table — no partitioning needed
-- reviews: Append-only, queried by order_id or customer_id
PARTITION BY DATE(_airbyte_extracted_at)
CLUSTER BY order_id

-- suppliers: Small, deduped
PARTITION BY DATE(_airbyte_extracted_at)
CLUSTER BY id
```

---

## Checking Partition & Clustering Usage

```sql
-- View partition metadata
SELECT
  partition_id,
  total_rows,
  total_logical_bytes,
  last_modified_time
FROM `project.postgres_raw.INFORMATION_SCHEMA.PARTITIONS`
WHERE table_name = 'orders'
ORDER BY partition_id DESC;

-- Estimate query cost before running (dry run via CLI)
-- bq query --dry_run --use_legacy_sql=false 'SELECT ...'

-- Check if clustering is being used (execution details in BQ Console)
-- Look for "blocks read" < "total blocks" in query stats
```
