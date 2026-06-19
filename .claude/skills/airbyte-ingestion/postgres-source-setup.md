# PostgreSQL Source Setup — Reference

## 1. Create Dedicated Airbyte User

```sql
-- Create user with minimal privileges
CREATE USER airbyte_user WITH PASSWORD 'your_password';

-- Grant read access to all current tables
GRANT CONNECT ON DATABASE supply_chain TO airbyte_user;
GRANT USAGE ON SCHEMA public TO airbyte_user;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO airbyte_user;

-- Ensure new tables created in the future are also accessible
ALTER DEFAULT PRIVILEGES IN SCHEMA public
  GRANT SELECT ON TABLES TO airbyte_user;
```

## 2. Configure pg_hba.conf

Add this line to allow Airbyte container to connect:

```
# pg_hba.conf
host    all    airbyte_user    0.0.0.0/0    md5
```

After editing, reload without restart:

```sql
SELECT pg_reload_conf();
```

Or via Docker:

```bash
docker exec supply_chain_postgres psql -U postgres -c "SELECT pg_reload_conf();"
```

## 3. WAL Configuration (only for CDC)

CDC requires logical replication. Edit `postgresql.conf`:

```conf
wal_level = logical
max_replication_slots = 5   # one per Airbyte connection
max_wal_senders = 5
```

Apply via Docker:

```bash
# Requires container restart to take effect
docker restart supply_chain_postgres

# Verify
docker exec supply_chain_postgres psql -U postgres -c "SHOW wal_level;"
```

Grant replication privilege to airbyte_user:

```sql
ALTER USER airbyte_user REPLICATION;
```

Create the replication slot (Airbyte can do this automatically, but manual creation gives more control):

```sql
SELECT pg_create_logical_replication_slot('airbyte_slot', 'pgoutput');

-- Verify
SELECT slot_name, plugin, active FROM pg_replication_slots;
```

## 4. Standard Extraction vs CDC — When to Use Each

| Method | Airbyte Mode | Requires | Use when |
|---|---|---|---|
| Cursor-based | Incremental Append / Deduped | `updated_at` column | Most tables; simpler setup |
| CDC (Debezium) | CDC | WAL logical replication | Need real-time, hard-delete tracking, or no cursor field |
| Full scan | Full Refresh | Nothing | Reference tables, no cursor |

**CDC trade-offs:**
- Pro: Captures hard deletes, low latency, no cursor dependency
- Con: More complex setup, replication slot must stay active (can grow WAL if Airbyte pauses)

## 5. Validate Connectivity from Airbyte Container

```bash
# Test that Airbyte can reach PostgreSQL by service name
docker exec airbyte-server psql \
  -h postgres \
  -U airbyte_user \
  -d supply_chain \
  -c "SELECT current_database(), current_user;"
```

If `psql` is not available in the Airbyte container:

```bash
# Use nc to test port reachability
docker exec airbyte-server nc -zv postgres 5432
```

## 6. Schema Discovery Verification

Before configuring Airbyte, confirm all target tables are visible to airbyte_user:

```sql
-- Run as airbyte_user
SELECT table_name
FROM information_schema.tables
WHERE table_schema = 'public'
  AND table_type = 'BASE TABLE'
ORDER BY table_name;
```

Expected supply chain tables:
- customers
- geolocation
- order_items
- orders
- payments
- products
- reviews
- suppliers
