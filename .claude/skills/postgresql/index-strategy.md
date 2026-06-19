# Index Strategy — Reference

## Index Type Selection

```
What kind of query are you optimizing?
│
├── Equality / range on a single column (=, <, >, BETWEEN)
│   └── B-tree (default) ✓
│
├── Full-text search or LIKE '%term%'
│   └── GIN with pg_trgm extension
│
├── JSONB column queries
│   └── GIN on the JSONB column
│
├── Array contains / overlap
│   └── GIN
│
├── Time-series with large date range, append-only table
│   └── BRIN (much smaller than B-tree, works on physically ordered data)
│
└── Geometric / geospatial
    └── GiST
```

Most supply chain queries use **B-tree** (primary keys, foreign keys, timestamps, status filters).

---

## Essential Indexes for Supply Chain Tables

```sql
-- orders: cursor column + most frequent join/filter columns
CREATE INDEX idx_orders_updated_at  ON orders (updated_at);
CREATE INDEX idx_orders_customer_id ON orders (customer_id);
CREATE INDEX idx_orders_status      ON orders (status) WHERE status IN ('pending', 'processing');

-- order_items: always filtered by order_id
CREATE INDEX idx_order_items_order_id   ON order_items (order_id);
CREATE INDEX idx_order_items_product_id ON order_items (product_id);
CREATE INDEX idx_order_items_created_at ON order_items (created_at);

-- payments: cursor + FK
CREATE INDEX idx_payments_updated_at ON payments (updated_at);
CREATE INDEX idx_payments_order_id   ON payments (order_id);

-- customers: cursor only (PK already indexed)
CREATE INDEX idx_customers_updated_at ON customers (updated_at);

-- products: cursor + category if filtered often
CREATE INDEX idx_products_updated_at ON products (updated_at);

-- reviews: cursor (usually insert-only)
CREATE INDEX idx_reviews_created_at ON reviews (created_at);
CREATE INDEX idx_reviews_order_id   ON reviews (order_id);

-- suppliers: cursor
CREATE INDEX idx_suppliers_updated_at ON suppliers (updated_at);
```

---

## Partial Indexes

Index only the rows that match a frequent WHERE condition — smaller and faster than a full index:

```sql
-- Only index pending/processing orders (active work queue pattern)
CREATE INDEX idx_orders_active
  ON orders (updated_at, customer_id)
  WHERE status IN ('pending', 'processing');

-- Only index unpaid payments
CREATE INDEX idx_payments_pending
  ON payments (order_id)
  WHERE status = 'pending';
```

**When to use:** filter column has low cardinality but queries always target a specific value subset.

---

## Covering Indexes (Index-Only Scans)

The `INCLUDE` clause adds non-key columns so PostgreSQL can answer the query from the index alone, without fetching the heap:

```sql
-- Airbyte cursor query: SELECT id, updated_at WHERE updated_at > $1
-- With this index, heap fetch is avoided entirely
CREATE INDEX idx_orders_cursor_covering
  ON orders (updated_at)
  INCLUDE (id);

-- Dashboard query: count + status without hitting table
CREATE INDEX idx_orders_status_covering
  ON orders (status)
  INCLUDE (id, total_amount);
```

**When to use:** a query selects only a few extra columns beyond the filter column.

---

## Index Maintenance

```sql
-- Find unused indexes (waste of write overhead)
SELECT
  schemaname,
  tablename,
  indexname,
  idx_scan   AS times_used,
  pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
WHERE idx_scan = 0
  AND indexrelname NOT LIKE '%pkey%'
ORDER BY pg_relation_size(indexrelid) DESC;

-- Find missing indexes (high sequential scan rate on large tables)
SELECT
  relname                                         AS table_name,
  seq_scan,
  idx_scan,
  seq_scan - idx_scan                             AS seq_over_idx,
  pg_size_pretty(pg_relation_size(relid))         AS table_size
FROM pg_stat_user_tables
WHERE seq_scan > idx_scan
  AND pg_relation_size(relid) > 10 * 1024 * 1024  -- only tables > 10 MB
ORDER BY seq_over_idx DESC;

-- Rebuild bloated indexes (after large deletes/updates)
REINDEX INDEX CONCURRENTLY idx_orders_updated_at;

-- Check index bloat
SELECT
  indexrelname,
  pg_size_pretty(pg_relation_size(indexrelid)) AS index_size
FROM pg_stat_user_indexes
ORDER BY pg_relation_size(indexrelid) DESC;
```

---

## Index Anti-Patterns

| Anti-pattern | Problem | Fix |
|---|---|---|
| Index on every column | Write overhead; planner confusion | Index only query-critical columns |
| B-tree on `LIKE '%term%'` | Index never used | Use GIN + pg_trgm |
| Index on low-cardinality column without partial | Planner ignores it | Use partial index for specific values |
| Redundant index (a,b) when (a) already exists | Wastes space | Drop the less specific one |
| Index created without `CONCURRENTLY` on live table | Locks the table | Always use `CREATE INDEX CONCURRENTLY` in production |
