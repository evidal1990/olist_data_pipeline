# Source Readiness Assessment — Reference

Before configuring any connector, run this assessment against the source table.

## Assessment Queries (PostgreSQL)

```sql
-- 1. Does a primary key exist?
SELECT constraint_name, column_name
FROM information_schema.key_column_usage
WHERE table_name = 'your_table'
  AND constraint_name LIKE '%pkey%';

-- 2. Does updated_at exist and is it populated?
SELECT
  COUNT(*)                          AS total_rows,
  COUNT(updated_at)                 AS rows_with_cursor,
  MAX(updated_at)                   AS latest_update,
  MIN(updated_at)                   AS earliest_update
FROM your_table;

-- 3. Check if updated_at actually updates on record changes
-- Run before and after updating a test record:
SELECT id, updated_at FROM your_table WHERE id = <test_id>;

-- 4. Volume assessment
SELECT
  pg_size_pretty(pg_total_relation_size('your_table')) AS table_size,
  reltuples::BIGINT                                    AS estimated_rows
FROM pg_class
WHERE relname = 'your_table';

-- 5. Detect soft vs hard delete pattern
SELECT column_name
FROM information_schema.columns
WHERE table_name = 'your_table'
  AND column_name IN ('deleted_at', 'is_deleted', 'active', 'status');
```

## Decision Matrix

| Condition | Verdict | Action |
|---|---|---|
| No PK + No cursor | Full Refresh only | Schedule infrequently; monitor cost |
| Has cursor, no PK | Incremental Append | Only if insert-only; document assumption |
| Has PK + cursor | Incremental Deduped | Preferred for entities |
| Cursor nullable > 5% | Full Refresh | Fix source or accept gap |
| Hard deletes used | Full Refresh or accept gap | Discuss with data owner |
| Table > 10GB | Avoid Full Refresh | Fix source to add cursor |

## Red Flags

- `updated_at` is set only on INSERT, not UPDATE (common ORM misconfiguration)
- Primary key is a composite key — some connectors handle this poorly; verify connector docs
- Table has no indexes on cursor field — incremental queries will be slow; request index
- Cursor is a `date` type, not `timestamp` — risk of missing intra-day updates in high-frequency syncs

## Source Checklist Output Template

```
Table: <schema>.<table>
Primary key: <column> | NONE
Cursor field: <column> | NONE
Cursor nullable: <N rows null> / <total rows>
Soft deletes: YES (deleted_at) | NO (hard delete) | N/A
Estimated size: <size>
Recommended strategy: <Full Refresh | Incremental Append | Incremental Append + Deduped>
Notes: <any red flags>
```
