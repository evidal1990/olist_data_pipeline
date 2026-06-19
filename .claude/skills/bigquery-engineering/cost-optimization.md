# Cost Optimization — Reference

## BigQuery Billing Model

**On-demand pricing:** charged per bytes scanned (not rows, not time).
- ~$5 USD per TB scanned (varies by region)
- First 1 TB/month free
- Streaming inserts: ~$0.01 per 200 MB inserted

**Flat-rate / capacity pricing:** reserved slots — relevant at scale, not for this project stage.

---

## The Highest-Cost Mistakes

| Mistake | Cost impact | Fix |
|---|---|---|
| `SELECT *` on large tables | Scans all columns | Select only needed columns |
| Query without partition filter | Full table scan | Always filter on partition column |
| Streaming inserts instead of batch | ~10x insert cost | Use GCS staging in Airbyte (batch load) |
| Querying `INFORMATION_SCHEMA` in loops | Billed per query | Cache results in a variable or temp table |
| Wildcard queries (`table_*`) without date suffix filter | May scan all matching tables | Add `_TABLE_SUFFIX` filter |
| No partition expiration | Storage grows forever | Set `partition_expiration_days` |

---

## Query Patterns — Cost-Safe vs Expensive

```sql
-- ❌ EXPENSIVE: scans all columns, all partitions
SELECT *
FROM `project.postgres_raw.orders`;

-- ✅ CHEAP: selects columns, filters partition
SELECT id, customer_id, status, updated_at
FROM `project.postgres_raw.orders`
WHERE DATE(_airbyte_extracted_at) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY);

-- ❌ EXPENSIVE: function on partition column breaks pruning
SELECT COUNT(*)
FROM `project.postgres_raw.orders`
WHERE EXTRACT(YEAR FROM _airbyte_extracted_at) = 2024;

-- ✅ CHEAP: direct range filter on partition column
SELECT COUNT(*)
FROM `project.postgres_raw.orders`
WHERE _airbyte_extracted_at >= '2024-01-01'
  AND _airbyte_extracted_at < '2025-01-01';
```

---

## Monitoring Daily Sync Cost

```sql
-- Cost estimate per table per sync date (bytes scanned by jobs)
SELECT
  destination_table.table_id                       AS table_name,
  DATE(creation_time)                              AS job_date,
  SUM(total_bytes_processed) / POW(1024, 3)        AS gb_processed,
  COUNT(*)                                          AS job_count
FROM `region-us.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
WHERE DATE(creation_time) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
  AND job_type = 'QUERY'
  AND state = 'DONE'
GROUP BY 1, 2
ORDER BY gb_processed DESC;

-- Storage cost per table
SELECT
  table_id,
  ROUND(size_bytes / POW(1024, 3), 2) AS size_gb,
  row_count
FROM `project.postgres_raw.__TABLES__`
ORDER BY size_bytes DESC;
```

---

## Airbyte-Specific Cost Controls

**Use GCS Staging (batch load), not Standard Inserts:**

In Airbyte BigQuery destination settings:
```
Loading Method: GCS Staging
GCS Bucket: airbyte-staging-supply-chain
GCS Bucket Path: airbyte/
```

This uses BigQuery Load Jobs (free) instead of Streaming API (paid per MB).

**Sync frequency vs cost trade-off:**

| Frequency | Cost profile | Risk |
|---|---|---|
| Every 15 min | High (many small loads) | More jobs, more overhead |
| Every 1 hour | Moderate | Good balance for operational data |
| Every 6 hours | Low | Acceptable lag for entity tables |
| Daily | Very low | Only for reference/static data |

Start with hourly for transactional tables; reduce if cost is a concern.

---

## Estimating Query Cost Before Running

```bash
# CLI dry run — returns bytes that would be scanned
bq query \
  --dry_run \
  --use_legacy_sql=false \
  'SELECT id, status FROM `project.postgres_raw.orders` WHERE DATE(_airbyte_extracted_at) = "2024-06-01"'
```

In BigQuery Console: look at the top-right validator — it shows bytes to be scanned before you run the query.

---

## Cost Guardrails

```sql
-- Enforce partition filter on large tables to prevent runaway scans
ALTER TABLE `project.postgres_raw.orders`
SET OPTIONS (require_partition_filter = TRUE);

-- Set partition expiration to avoid unbounded storage growth
ALTER TABLE `project.postgres_raw.orders`
SET OPTIONS (partition_expiration_days = 365);
```
