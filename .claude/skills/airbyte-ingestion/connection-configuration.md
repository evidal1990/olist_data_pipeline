# Airbyte Connection Configuration — Reference

## Source Connector Settings (PostgreSQL)

| Field | Value | Notes |
|---|---|---|
| Host | `postgres` | Service name from docker-compose, NOT `localhost` |
| Port | `5432` | Default PostgreSQL port |
| Database | `supply_chain` | Target database name |
| Username | `airbyte_user` | Dedicated read-only user |
| Password | (secret) | Store in Airbyte secrets, not plaintext |
| SSL | Disable | Internal Docker network; enable for external sources |
| Replication Method | Standard / CDC | See decision below |
| Schemas | `public` | Explicitly list; avoid `information_schema` |

### Replication Method

```
Need hard-delete detection or real-time latency < 1 min?
├── YES → CDC (Debezium)
│         Requires: wal_level=logical, replication slot, REPLICATION privilege
└── NO  → Standard
          Cursor-based; simpler; sufficient for most batch use cases
```

---

## Destination Connector Settings (BigQuery)

| Field | Value | Notes |
|---|---|---|
| Project ID | `your-gcp-project` | GCP project where BigQuery lives |
| Dataset Location | `US` or `southamerica-east1` | Match where data will be queried |
| Default Dataset ID | `postgres_raw` | Landing dataset for raw tables |
| Loading Method | GCS Staging | Preferred for tables > 100k rows/sync |
| GCS Bucket | `airbyte-staging-supply-chain` | Temp storage during load |
| Service Account Key | (JSON key file) | Must have BigQuery + GCS permissions |

### Loading Method Trade-offs

| Method | Speed | Cost | Use when |
|---|---|---|---|
| Standard Inserts | Slow for large loads | Higher DML cost | Dev/test, small tables |
| GCS Staging | Fast | Lower (batch load) | Production, any table > 100k rows |

---

## Stream Configuration (per table)

In the Airbyte UI, after source/destination are set, configure each stream:

### Sync Mode Selection per Stream

| Table | Source Mode | Destination Mode | Cursor | PK |
|---|---|---|---|---|
| orders | Incremental | Append + Deduped | updated_at | id |
| order_items | Incremental | Append | created_at | id |
| customers | Incremental | Append + Deduped | updated_at | id |
| products | Incremental | Append + Deduped | updated_at | id |
| suppliers | Incremental | Append + Deduped | updated_at | id |
| payments | Incremental | Append + Deduped | updated_at | id |
| reviews | Incremental | Append | created_at | id |
| geolocation | Full Refresh | Overwrite | — | — |

### Namespace Mapping

```
Source namespace: public
Destination namespace: ${SOURCE_NAMESPACE}   # maps to 'public' in BigQuery dataset
```

This keeps table names as `postgres_raw.public_orders` in BigQuery. To flatten:

```
Destination namespace: postgres_raw
Destination stream prefix: (empty)
```

Result: `postgres_raw.orders` — cleaner for downstream use.

---

## Sync Schedule

| Frequency | Use when |
|---|---|
| Every 1 hour | Operational data needing near-real-time (orders, payments) |
| Every 6 hours | Entities that change less (customers, products) |
| Every 24 hours | Reference data (geolocation) or Full Refresh tables |
| Manual | Initial load; backfills |

Start with longer intervals and shorten as observability confirms reliability.

---

## Post-Connection Validation

After first sync, verify in BigQuery:

```sql
-- 1. All tables arrived
SELECT table_name
FROM `project.postgres_raw.INFORMATION_SCHEMA.TABLES`
ORDER BY table_name;

-- 2. Row count matches source
SELECT COUNT(*) FROM `project.postgres_raw.orders`;

-- 3. Metadata columns present
SELECT
  _airbyte_raw_id,
  _airbyte_extracted_at,
  _airbyte_meta
FROM `project.postgres_raw.orders`
LIMIT 5;

-- 4. No unexpected nulls on key columns
SELECT
  COUNTIF(id IS NULL)         AS null_ids,
  COUNTIF(updated_at IS NULL) AS null_cursors
FROM `project.postgres_raw.orders`;
```
