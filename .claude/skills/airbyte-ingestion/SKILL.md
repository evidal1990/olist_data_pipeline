---
name: airbyte-ingestion
description: Use when configuring Airbyte to ingest data from a PostgreSQL source running in Docker into BigQuery. Use when setting up a new source connector, configuring streams, choosing sync modes, or troubleshooting connectivity between Airbyte and PostgreSQL containers.
---

# Airbyte Ingestion — PostgreSQL (Docker) → BigQuery

## Overview

Ingesting from PostgreSQL in Docker has one critical non-obvious constraint: **Airbyte cannot reach `localhost`**. Both containers must share a Docker network and Airbyte must reference PostgreSQL by container/service name.

See supporting files for detailed steps:
- [postgres-source-setup.md](postgres-source-setup.md) — user creation, permissions, WAL config
- [connection-configuration.md](connection-configuration.md) — Airbyte UI settings, stream config, sync modes

---

## Pre-flight Checklist

Before opening Airbyte UI:

- [ ] PostgreSQL and Airbyte containers are on the same Docker network
- [ ] PostgreSQL has a dedicated read-only user for Airbyte
- [ ] `pg_hba.conf` allows connections from Airbyte container IP/network
- [ ] If using CDC: `wal_level = logical` is set and a replication slot exists
- [ ] BigQuery service account has `BigQuery Data Editor` + `BigQuery Job User` roles
- [ ] GCS bucket created (if using GCS staging for large volumes)

---

## Docker Network — Critical

```yaml
# docker-compose.yml — both services must share the same network
services:
  postgres:
    image: postgres:15
    container_name: supply_chain_postgres
    networks:
      - data_platform

  airbyte-server:
    image: airbyte/server:latest
    networks:
      - data_platform

networks:
  data_platform:
    driver: bridge
```

In Airbyte source config, set **Host** to the PostgreSQL **service name** (`postgres`), not `localhost`.

---

## Sync Mode — Quick Decision

```
Table has updated_at?
├── NO  → Full Refresh
└── YES → Has primary key?
          ├── NO  → Incremental Append
          └── YES → Records update/delete?
                    ├── NO  → Incremental Append
                    └── YES → Incremental Deduped History
```

**REQUIRED SKILL:** See `data-architecture` for full sync strategy reasoning and supply chain entity reference.

---

## Common Errors

| Error | Cause | Fix |
|---|---|---|
| `Connection refused` on localhost | Airbyte can't reach host network | Use container/service name, not `localhost` |
| `pg_hba.conf` rejection | Airbyte IP not whitelisted | Add `host all airbyte_user 0.0.0.0/0 md5` to pg_hba |
| `permission denied for table` | User lacks SELECT grant | Run `GRANT SELECT ON ALL TABLES IN SCHEMA public TO airbyte_user` |
| `replication slot already exists` | Previous CDC attempt | Drop slot: `SELECT pg_drop_replication_slot('airbyte_slot')` |
| BigQuery `Access Denied` | Service account missing roles | Add `BigQuery Data Editor` + `BigQuery Job User` |
