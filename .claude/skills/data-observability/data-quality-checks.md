# Data Quality Checks — Reference

## 1. Null Check on Critical Columns

```sql
-- Detect unexpected nulls on columns that should never be null
SELECT
  'orders' AS table_name,
  COUNTIF(id IS NULL)          AS null_id,
  COUNTIF(customer_id IS NULL) AS null_customer_id,
  COUNTIF(status IS NULL)      AS null_status,
  COUNTIF(created_at IS NULL)  AS null_created_at,
  COUNTIF(updated_at IS NULL)  AS null_updated_at,
  COUNT(*)                     AS total_rows
FROM `project.postgres_raw.orders`
WHERE DATE(_airbyte_extracted_at) = CURRENT_DATE();
```

Repeat per table. If `null_id > 0`, the primary key column has gaps — investigate source or Airbyte stream config.

---

## 2. Duplicate Detection (Deduped Tables)

For tables configured with Incremental Append + Deduped, the destination should have unique IDs. If duplicates appear, the dedup isn't working:

```sql
-- Find duplicate primary keys
SELECT
  id,
  COUNT(*) AS occurrences
FROM `project.postgres_raw.orders`
GROUP BY id
HAVING COUNT(*) > 1
ORDER BY occurrences DESC
LIMIT 20;
```

**Cause of duplicates:**
- Airbyte stream not configured with correct primary key
- Full Refresh ran on a Deduped table (creates duplicates until dedup job runs)
- Multiple Airbyte connections writing to the same destination table

---

## 3. Value Range & Enum Validation

```sql
-- orders: status should only contain known values
SELECT status, COUNT(*) AS cnt
FROM `project.postgres_raw.orders`
WHERE DATE(_airbyte_extracted_at) >= DATE_SUB(CURRENT_DATE(), INTERVAL 7 DAY)
GROUP BY status
ORDER BY cnt DESC;

-- payments: amount should never be negative
SELECT
  COUNT(*) AS negative_amounts
FROM `project.postgres_raw.payments`
WHERE total_amount < 0;

-- order_items: quantity should be a positive integer
SELECT
  COUNT(*) AS invalid_quantity
FROM `project.postgres_raw.order_items`
WHERE quantity <= 0 OR quantity IS NULL;
```

---

## 4. Referential Integrity Checks

Detects orphaned records — rows that reference a parent that doesn't exist:

```sql
-- order_items with no matching order
SELECT COUNT(*) AS orphaned_items
FROM `project.postgres_raw.order_items` oi
LEFT JOIN `project.postgres_raw.orders` o ON oi.order_id = o.id
WHERE o.id IS NULL;

-- payments with no matching order
SELECT COUNT(*) AS orphaned_payments
FROM `project.postgres_raw.payments` p
LEFT JOIN `project.postgres_raw.orders` o ON p.order_id = o.id
WHERE o.id IS NULL;
```

**Non-zero result is normal** if orders and order_items sync at different times. If count keeps growing, investigate.

---

## 5. Schema Drift Detection

Airbyte can silently add columns when the source schema changes. Track column count over time:

```sql
-- Current column count per table
SELECT
  table_name,
  COUNT(*) AS column_count
FROM `project.postgres_raw.INFORMATION_SCHEMA.COLUMNS`
WHERE table_schema = 'postgres_raw'
GROUP BY table_name
ORDER BY table_name;
```

Compare this against a baseline. If a table has more columns than expected:

```sql
-- List all columns for a specific table
SELECT column_name, data_type, is_nullable
FROM `project.postgres_raw.INFORMATION_SCHEMA.COLUMNS`
WHERE table_name = 'orders'
ORDER BY ordinal_position;
```

**Schema drift signals:**
- New column appears with all NULLs (source added a column, not yet populated)
- Column type changed (STRING → INT64) — can break downstream queries
- Column disappeared — Airbyte usually adds missing columns but won't remove them

---

## 6. Freshness Check at Source Level

Sometimes the pipeline is healthy but the source itself stopped writing. Verify at PostgreSQL:

```sql
-- Run against PostgreSQL source
SELECT
  'orders'    AS table_name, MAX(updated_at) AS latest_record, NOW() - MAX(updated_at) AS lag
FROM orders
UNION ALL
SELECT 'customers',   MAX(updated_at), NOW() - MAX(updated_at) FROM customers
UNION ALL
SELECT 'order_items', MAX(created_at), NOW() - MAX(created_at) FROM order_items
UNION ALL
SELECT 'payments',    MAX(updated_at), NOW() - MAX(updated_at) FROM payments
ORDER BY lag DESC;
```

If source lag is large, the problem is upstream of the pipeline — no ingestion fix will help.

---

## 7. Airbyte Metadata Integrity

Every row loaded by Airbyte must have metadata columns populated:

```sql
-- Check for missing Airbyte metadata (indicates a load problem)
SELECT
  COUNTIF(_airbyte_raw_id IS NULL)       AS null_raw_id,
  COUNTIF(_airbyte_extracted_at IS NULL) AS null_extracted_at,
  COUNT(*)                               AS total_rows
FROM `project.postgres_raw.orders`
WHERE DATE(_airbyte_extracted_at) = CURRENT_DATE();
```

`null_raw_id > 0` or `null_extracted_at > 0` indicates a malformed load — check Airbyte attempt logs.
