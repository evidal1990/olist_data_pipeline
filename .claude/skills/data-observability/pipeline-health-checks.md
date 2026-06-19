# Pipeline Health Checks — Reference

## 1. Data Freshness per Table

```sql
-- Last sync time and lag per table
SELECT
  table_name,
  last_sync,
  TIMESTAMP_DIFF(CURRENT_TIMESTAMP(), last_sync, MINUTE) AS lag_minutes
FROM (
  SELECT 'orders'    AS table_name, MAX(_airbyte_extracted_at) AS last_sync FROM `project.postgres_raw.orders`
  UNION ALL
  SELECT 'customers',   MAX(_airbyte_extracted_at) FROM `project.postgres_raw.customers`
  UNION ALL
  SELECT 'order_items', MAX(_airbyte_extracted_at) FROM `project.postgres_raw.order_items`
  UNION ALL
  SELECT 'payments',    MAX(_airbyte_extracted_at) FROM `project.postgres_raw.payments`
)
ORDER BY lag_minutes DESC;
```

---

## 2. Sync Volume Over Time

Detects drops in rows loaded per sync cycle:

```sql
-- Rows loaded per day per table
SELECT
  DATE(_airbyte_extracted_at) AS sync_date,
  COUNT(*)                    AS rows_loaded
FROM `project.postgres_raw.orders`
WHERE _airbyte_extracted_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 14 DAY)
GROUP BY 1
ORDER BY 1 DESC;
```

**What to look for:**
- A day with 0 rows = sync gap or source stopped writing
- Sudden large spike = potential Full Refresh or data reloaded incorrectly
- Gradual decrease = could indicate source is writing less (normal) or cursor drift

---

## 3. Sync Gap Detection

Identifies days where no data arrived:

```sql
WITH date_series AS (
  SELECT DATE(d) AS expected_date
  FROM UNNEST(GENERATE_DATE_ARRAY(
    DATE_SUB(CURRENT_DATE(), INTERVAL 14 DAY),
    CURRENT_DATE()
  )) AS d
),
actual_syncs AS (
  SELECT DISTINCT DATE(_airbyte_extracted_at) AS sync_date
  FROM `project.postgres_raw.orders`
  WHERE _airbyte_extracted_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 14 DAY)
)
SELECT expected_date, sync_date IS NULL AS gap_detected
FROM date_series
LEFT JOIN actual_syncs ON expected_date = sync_date
ORDER BY expected_date DESC;
```

---

## 4. Source vs Destination Row Count Comparison

Run from a tool that can query both PostgreSQL and BigQuery (e.g., a Python script):

```python
import psycopg2
from google.cloud import bigquery

pg_conn = psycopg2.connect("host=localhost dbname=supply_chain user=airbyte_user password=...")
bq_client = bigquery.Client(project="your-project")

tables = ["orders", "customers", "order_items", "products", "payments", "reviews", "suppliers"]

for table in tables:
    pg_cur = pg_conn.cursor()
    pg_cur.execute(f"SELECT COUNT(*) FROM {table}")
    pg_count = pg_cur.fetchone()[0]

    bq_query = f"SELECT COUNT(DISTINCT id) FROM `your-project.postgres_raw.{table}`"
    bq_count = list(bq_client.query(bq_query))[0][0]

    diff = pg_count - bq_count
    status = "OK" if abs(diff) < 10 else "DRIFT"
    print(f"{table:20s} | pg={pg_count:8d} | bq={bq_count:8d} | diff={diff:+d} | {status}")
```

**Expected:** small diff is normal (rows written after last sync). Large diff = investigate.

---

## 5. Watermark Monitoring (Incremental Cursor Drift)

If the same watermark appears for multiple consecutive days, the cursor is stuck:

```sql
-- Check if cursor is advancing
SELECT
  DATE(_airbyte_extracted_at)  AS sync_date,
  MAX(updated_at)              AS max_source_cursor,
  COUNT(*)                     AS rows_loaded
FROM `project.postgres_raw.orders`
WHERE _airbyte_extracted_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 7 DAY)
GROUP BY 1
ORDER BY 1 DESC;
```

**Cursor stuck = `max_source_cursor` is the same across multiple days.** Fix: reset Airbyte connection state or investigate source writes.

---

## 6. BigQuery Job Monitoring

```sql
-- Failed jobs in the last 24 hours
SELECT
  job_id,
  creation_time,
  end_time,
  error_result.message AS error_message,
  destination_table.table_id AS destination_table
FROM `region-us.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
WHERE DATE(creation_time) = CURRENT_DATE()
  AND state = 'DONE'
  AND error_result IS NOT NULL
ORDER BY creation_time DESC;

-- Slowest jobs (potential performance issue)
SELECT
  job_id,
  creation_time,
  TIMESTAMP_DIFF(end_time, start_time, SECOND)  AS duration_seconds,
  total_bytes_processed / POW(1024,3)           AS gb_processed,
  destination_table.table_id
FROM `region-us.INFORMATION_SCHEMA.JOBS_BY_PROJECT`
WHERE DATE(creation_time) = CURRENT_DATE()
  AND state = 'DONE'
  AND job_type = 'LOAD'
ORDER BY duration_seconds DESC
LIMIT 20;
```
