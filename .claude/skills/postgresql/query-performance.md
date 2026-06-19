# Query Performance — Reference

## EXPLAIN ANALYZE — Reading the Output

```sql
-- Always use ANALYZE + BUFFERS for real diagnosis
EXPLAIN (ANALYZE, BUFFERS, FORMAT TEXT)
SELECT o.id, o.status, c.name
FROM orders o
JOIN customers c ON o.customer_id = c.id
WHERE o.updated_at > '2024-01-01'
  AND o.status = 'pending';
```

### Key Fields to Read

| Field | What it means |
|---|---|
| `Seq Scan` | Full table scan — no index used (investigate if table is large) |
| `Index Scan` | Index used, then heap fetched per row |
| `Index Only Scan` | Index used, no heap fetch — fastest |
| `Bitmap Heap Scan` | Index used, rows batched before heap fetch — good for range queries |
| `cost=X..Y` | Estimated cost (X=startup, Y=total) — compare across plans |
| `actual time=X..Y` | Real execution time in ms |
| `rows=N` | Estimated rows (if far from actual, statistics are stale) |
| `actual rows=N` | Real rows returned |
| `Buffers: shared hit=N` | Pages read from cache (good) |
| `Buffers: shared read=N` | Pages read from disk (slower) |

### Statistics Stale? Update Them

If estimated rows differ wildly from actual rows, the planner is making bad decisions:

```sql
ANALYZE orders;          -- update statistics for one table
ANALYZE;                 -- update all tables
```

---

## Common Performance Anti-Patterns

### 1. Function on an Indexed Column in WHERE

```sql
-- ❌ Index on updated_at is ignored
WHERE DATE(updated_at) = '2024-06-01'
WHERE EXTRACT(YEAR FROM updated_at) = 2024

-- ✅ Index used
WHERE updated_at >= '2024-06-01' AND updated_at < '2024-06-02'
```

### 2. Implicit Type Cast Breaks Index

```sql
-- ❌ If id is INTEGER but compared to TEXT, cast happens, index ignored
WHERE id = '12345'

-- ✅ Match types exactly
WHERE id = 12345
```

### 3. OR Across Multiple Columns Disables Index

```sql
-- ❌ Hard to use indexes efficiently
WHERE customer_id = 1 OR order_id = 1

-- ✅ Use UNION instead
SELECT * FROM orders WHERE customer_id = 1
UNION
SELECT * FROM orders WHERE order_id = 1 AND customer_id != 1
```

### 4. SELECT * on Wide Tables

```sql
-- ❌ Fetches all columns including large TEXT/JSONB
SELECT * FROM orders WHERE updated_at > $1

-- ✅ Select only what's needed
SELECT id, customer_id, status, updated_at FROM orders WHERE updated_at > $1
```

### 5. NOT IN with NULL Values

```sql
-- ❌ Returns empty if subquery has any NULL
WHERE id NOT IN (SELECT customer_id FROM orders)

-- ✅ Use NOT EXISTS instead
WHERE NOT EXISTS (SELECT 1 FROM orders WHERE orders.customer_id = customers.id)
```

---

## Identifying Slow Queries

Enable `pg_stat_statements` (add to `postgresql.conf`):

```conf
shared_preload_libraries = 'pg_stat_statements'
pg_stat_statements.track = all
```

Then:

```sql
-- Top 10 slowest queries by total time
SELECT
  LEFT(query, 120)                    AS query_snippet,
  calls,
  ROUND(mean_exec_time::numeric, 2)   AS avg_ms,
  ROUND(total_exec_time::numeric, 2)  AS total_ms,
  rows / calls                        AS avg_rows
FROM pg_stat_statements
ORDER BY total_exec_time DESC
LIMIT 10;

-- Queries with worst row estimate accuracy (stale statistics)
SELECT
  LEFT(query, 120) AS query_snippet,
  calls,
  rows / calls     AS avg_actual_rows
FROM pg_stat_statements
ORDER BY calls DESC
LIMIT 20;
```

---

## Airbyte Cursor Query Performance

Airbyte runs a query like this for every incremental sync:

```sql
SELECT * FROM orders
WHERE updated_at > $last_cursor
ORDER BY updated_at ASC;
```

This must use an index on `updated_at`. Verify:

```sql
EXPLAIN (ANALYZE, BUFFERS)
SELECT id, customer_id, status, updated_at
FROM orders
WHERE updated_at > '2024-06-01 00:00:00'
ORDER BY updated_at ASC;
```

Expected: `Index Scan using idx_orders_updated_at` — not `Seq Scan`.

If you see `Seq Scan`, either:
- The index doesn't exist → create it
- The planner thinks a seq scan is faster (table is small or most rows match) → acceptable
- Statistics are stale → run `ANALYZE orders`

---

## Connection and Lock Monitoring

```sql
-- Active connections and their state
SELECT
  pid,
  usename,
  application_name,
  state,
  wait_event_type,
  wait_event,
  LEFT(query, 100) AS query_snippet,
  NOW() - query_start AS duration
FROM pg_stat_activity
WHERE state != 'idle'
ORDER BY duration DESC;

-- Lock conflicts (blocking queries)
SELECT
  blocked.pid          AS blocked_pid,
  blocked.query        AS blocked_query,
  blocking.pid         AS blocking_pid,
  blocking.query       AS blocking_query
FROM pg_stat_activity blocked
JOIN pg_stat_activity blocking
  ON blocking.pid = ANY(pg_blocking_pids(blocked.pid))
WHERE blocked.wait_event_type = 'Lock';

-- Kill a stuck query (use with caution)
SELECT pg_cancel_backend(pid);    -- sends SIGINT (graceful)
SELECT pg_terminate_backend(pid); -- sends SIGTERM (forced)
```
