---
name: postgresql
description: Use when designing PostgreSQL schemas, choosing index types, diagnosing slow queries, configuring PostgreSQL in Docker, ensuring updated_at columns are reliable for incremental sync, or auditing schema quality for a supply chain transactional database.
---

# PostgreSQL Engineering

## Overview

PostgreSQL is the source of truth. Schema quality, index strategy, and query performance at the source directly affect ingestion reliability and downstream data quality. The most common silent failure: `updated_at` that doesn't actually update on every write path.

See supporting files for detailed guidance:
- [index-strategy.md](index-strategy.md) — index types, selection guide, supply chain examples
- [query-performance.md](query-performance.md) — EXPLAIN ANALYZE, anti-patterns, optimization
- [schema-design.md](schema-design.md) — data types, constraints, audit columns, naming

---

## Critical Rules

- **Never modify source tables** — read-only access for Airbyte; schema changes go through migration scripts
- **`updated_at` must be enforced by a trigger**, not trusted from application code — ORMs and batch jobs routinely skip it
- **A sequential scan on a large table during Airbyte sync can degrade production** — add indexes on cursor columns
- **Autovacuum must run regularly** — stale dead tuples inflate row counts and skew `updated_at` cursor accuracy

---

## Non-Obvious PostgreSQL Behaviors

| Behavior | Why it matters |
|---|---|
| `SELECT COUNT(*)` is slow on large tables | No index covers all rows; use `pg_class.reltuples` for estimates |
| Index is ignored on low-cardinality columns | Planner chooses seq scan when selectivity is poor (e.g., status with 3 values) |
| `EXPLAIN` doesn't run the query; `EXPLAIN ANALYZE` does | Cost estimates in `EXPLAIN` can be wrong; always use `ANALYZE` for diagnosis |
| Updates create dead tuples — autovacuum cleans them | High update rate tables need `autovacuum_vacuum_scale_factor` tuned down |
| `LIKE '%term%'` never uses a B-tree index | Use `pg_trgm` GIN index for substring search |
| Partial indexes beat full indexes for filtered queries | `WHERE status = 'pending'` index is much smaller and faster than full index |

---

## Supply Chain Schema — Quick Audit

Run this to check which tables are missing critical columns:

```sql
SELECT
  t.table_name,
  MAX(CASE WHEN c.column_name = 'id'         THEN 'YES' END) AS has_id,
  MAX(CASE WHEN c.column_name = 'created_at' THEN 'YES' END) AS has_created_at,
  MAX(CASE WHEN c.column_name = 'updated_at' THEN 'YES' END) AS has_updated_at
FROM information_schema.tables t
LEFT JOIN information_schema.columns c
  ON t.table_name = c.table_name AND t.table_schema = c.table_schema
WHERE t.table_schema = 'public'
  AND t.table_type = 'BASE TABLE'
GROUP BY t.table_name
ORDER BY t.table_name;
```

Any table with `has_updated_at = NULL` cannot support reliable incremental sync.

---

## Docker Configuration Essentials

Key `postgresql.conf` settings for a containerized supply chain DB:

```conf
# Connections
max_connections = 200           # default 100 is often too low

# Memory (adjust based on container memory limit)
shared_buffers = 256MB          # ~25% of container RAM
work_mem = 16MB                 # per sort/hash operation
maintenance_work_mem = 128MB    # for VACUUM, CREATE INDEX

# WAL (required for Airbyte CDC)
wal_level = logical
max_replication_slots = 5
max_wal_senders = 5

# Autovacuum (tune for high-update tables)
autovacuum_vacuum_scale_factor = 0.05   # trigger at 5% dead tuples (default 20%)
autovacuum_analyze_scale_factor = 0.02
```

Apply without restart (most settings):
```bash
docker exec supply_chain_postgres psql -U postgres -c "SELECT pg_reload_conf();"
```

WAL level and max_connections require restart:
```bash
docker restart supply_chain_postgres
```
