# Schema Design — Reference

## Audit Columns — Required on Every Table

Every table must have these columns to support incremental sync and auditability:

```sql
id         BIGSERIAL PRIMARY KEY,
created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
```

**`updated_at` must be enforced by a trigger** — application code alone is unreliable:

```sql
-- Reusable function
CREATE OR REPLACE FUNCTION set_updated_at()
RETURNS TRIGGER AS $$
BEGIN
  NEW.updated_at = NOW();
  RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Apply to each table
CREATE TRIGGER trg_orders_updated_at
  BEFORE UPDATE ON orders
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

CREATE TRIGGER trg_customers_updated_at
  BEFORE UPDATE ON customers
  FOR EACH ROW EXECUTE FUNCTION set_updated_at();

-- Verify trigger exists
SELECT trigger_name, event_manipulation, event_object_table
FROM information_schema.triggers
WHERE trigger_schema = 'public'
ORDER BY event_object_table;
```

---

## Data Type Selection

| Use case | Recommended type | Avoid |
|---|---|---|
| Primary key | `BIGSERIAL` or `UUID` | `SERIAL` (limited to 2B rows) |
| Foreign key | `BIGINT` (match PK type) | `INTEGER` if PK is BIGINT |
| Monetary values | `NUMERIC(12, 2)` | `FLOAT` / `DOUBLE PRECISION` (rounding errors) |
| Timestamps | `TIMESTAMP WITH TIME ZONE` | `TIMESTAMP` (no timezone = ambiguous) |
| Status / enum | `VARCHAR(50)` + CHECK constraint | PostgreSQL `ENUM` type (hard to migrate) |
| Short text | `VARCHAR(N)` with realistic N | `TEXT` for everything (loses intent) |
| Long text / descriptions | `TEXT` | `VARCHAR(10000)` (arbitrary limit) |
| Boolean flags | `BOOLEAN NOT NULL DEFAULT FALSE` | `SMALLINT` (legacy pattern) |
| Geolocation | `NUMERIC(9,6)` for lat/lon | `FLOAT` |

### Why Avoid PostgreSQL ENUM?

```sql
-- ❌ Hard to modify without table lock
CREATE TYPE order_status AS ENUM ('pending', 'processing', 'shipped', 'delivered');

-- ✅ Flexible and migrateable
status VARCHAR(50) NOT NULL DEFAULT 'pending'
  CHECK (status IN ('pending', 'processing', 'shipped', 'delivered', 'cancelled'))
```

Adding a value to a `CHECK` constraint is a metadata-only operation. Adding to an ENUM type requires `ALTER TYPE` which can lock in some versions.

---

## Naming Conventions

| Object | Convention | Example |
|---|---|---|
| Tables | `snake_case`, plural | `orders`, `order_items` |
| Columns | `snake_case` | `customer_id`, `total_amount` |
| Primary key | `id` | `id` |
| Foreign key | `<table_singular>_id` | `order_id`, `customer_id` |
| Index | `idx_<table>_<columns>` | `idx_orders_updated_at` |
| Trigger | `trg_<table>_<purpose>` | `trg_orders_updated_at` |
| Function | `snake_case` verb | `set_updated_at()` |
| Constraint | `chk_<table>_<rule>` | `chk_payments_positive_amount` |

---

## Constraints for Data Integrity

```sql
-- NOT NULL on business-critical columns
ALTER TABLE orders
  ALTER COLUMN customer_id SET NOT NULL,
  ALTER COLUMN status SET NOT NULL,
  ALTER COLUMN total_amount SET NOT NULL;

-- CHECK constraints for valid values
ALTER TABLE orders
  ADD CONSTRAINT chk_orders_status
    CHECK (status IN ('pending', 'processing', 'shipped', 'delivered', 'cancelled'));

ALTER TABLE payments
  ADD CONSTRAINT chk_payments_positive_amount
    CHECK (total_amount >= 0);

ALTER TABLE order_items
  ADD CONSTRAINT chk_order_items_quantity
    CHECK (quantity > 0);

-- Foreign key constraints (with appropriate ON DELETE)
ALTER TABLE order_items
  ADD CONSTRAINT fk_order_items_order
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE CASCADE;

ALTER TABLE payments
  ADD CONSTRAINT fk_payments_order
    FOREIGN KEY (order_id) REFERENCES orders(id) ON DELETE RESTRICT;
```

---

## Supply Chain Table Templates

```sql
CREATE TABLE orders (
  id          BIGSERIAL PRIMARY KEY,
  customer_id BIGINT    NOT NULL REFERENCES customers(id),
  status      VARCHAR(50) NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending', 'processing', 'shipped', 'delivered', 'cancelled')),
  total_amount NUMERIC(12, 2) NOT NULL CHECK (total_amount >= 0),
  created_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  updated_at  TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);

CREATE TABLE order_items (
  id         BIGSERIAL PRIMARY KEY,
  order_id   BIGINT NOT NULL REFERENCES orders(id) ON DELETE CASCADE,
  product_id BIGINT NOT NULL REFERENCES products(id),
  quantity   INTEGER NOT NULL CHECK (quantity > 0),
  unit_price NUMERIC(12, 2) NOT NULL CHECK (unit_price >= 0),
  created_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE NOT NULL DEFAULT NOW()
);
```

---

## Soft Delete Pattern

When records must not be hard-deleted (audit requirements, referential integrity):

```sql
-- Add soft delete column
ALTER TABLE orders ADD COLUMN deleted_at TIMESTAMP WITH TIME ZONE;

-- Query active records
SELECT * FROM orders WHERE deleted_at IS NULL;

-- Partial index for active records only (much smaller)
CREATE INDEX idx_orders_active_updated_at
  ON orders (updated_at)
  WHERE deleted_at IS NULL;

-- Airbyte can detect soft deletes via updated_at change
-- deleted_at becoming non-null triggers an updated_at update (via trigger)
```

---

## Table Bloat and Vacuum

PostgreSQL UPDATE creates a new row version (dead tuple). Without vacuum, tables bloat:

```sql
-- Check table bloat and autovacuum status
SELECT
  relname                              AS table_name,
  n_live_tup,
  n_dead_tup,
  ROUND(100.0 * n_dead_tup / NULLIF(n_live_tup + n_dead_tup, 0), 1) AS dead_pct,
  last_autovacuum,
  last_autoanalyze
FROM pg_stat_user_tables
ORDER BY n_dead_tup DESC;

-- Manually vacuum a high-update table
VACUUM ANALYZE orders;

-- Aggressive vacuum (reclaims disk space, more disruptive)
VACUUM FULL ANALYZE orders;  -- locks table; use only in maintenance window
```

**If `dead_pct > 20%` on orders or payments**, autovacuum settings need tuning — see `postgresql.conf` settings in `SKILL.md`.
