# Airbyte Monitoring — Reference

## 1. Job Status via Airbyte UI

Navigate to: **Connections → [Connection name] → Job History**

Each job shows:
- Status: Succeeded / Failed / Cancelled
- Rows synced
- Duration
- Error message (if failed)

**Key distinction:**
- `Succeeded with 0 rows` = sync ran but no new data found (normal for quiet periods; abnormal if source is active)
- `Failed` = investigate attempt logs
- `Partially succeeded` = some streams failed; check which ones

---

## 2. Reading Airbyte Logs (Docker)

```bash
# Airbyte server logs (general platform logs)
docker logs airbyte-server --tail 100

# Follow logs in real time
docker logs airbyte-server -f

# Worker logs (actual sync execution)
docker logs airbyte-worker --tail 200

# Filter for errors only
docker logs airbyte-worker 2>&1 | grep -i "error\|exception\|failed"

# Filter for a specific connection or job
docker logs airbyte-worker 2>&1 | grep "connection-id-here"
```

---

## 3. Common Error Patterns in Logs

| Log pattern | Meaning | Fix |
|---|---|---|
| `Connection refused` to postgres | Can't reach source | Check Docker network; use service name not localhost |
| `FATAL: password authentication failed` | Wrong credentials | Verify airbyte_user password in source config |
| `permission denied for table` | Missing SELECT grant | Run `GRANT SELECT ON ALL TABLES` in PostgreSQL |
| `replication slot ... does not exist` | CDC slot was dropped | Recreate slot or switch to Standard replication |
| `WAL level not logical` | PostgreSQL not configured for CDC | Set `wal_level=logical` and restart container |
| `Quota exceeded` | Too many concurrent BQ jobs | Stagger sync schedules |
| `JsonSchemaReferenceException` | Schema mismatch source vs destination | Refresh source schema in Airbyte connection |
| `stream ... not found` | Table was dropped or renamed | Update stream list in Airbyte connection |

---

## 4. Airbyte API for Programmatic Monitoring

Airbyte exposes a REST API for querying job status:

```bash
# List recent jobs for a connection
curl -X GET "http://localhost:8001/api/v1/jobs/list" \
  -H "Content-Type: application/json" \
  -d '{
    "configId": "your-connection-id",
    "configType": "sync",
    "includingJobId": 0,
    "pageSize": 10
  }'

# Get job details (including attempt logs)
curl -X GET "http://localhost:8001/api/v1/jobs/get" \
  -H "Content-Type: application/json" \
  -d '{"id": 123}'

# Trigger a manual sync
curl -X POST "http://localhost:8001/api/v1/connections/sync" \
  -H "Content-Type: application/json" \
  -d '{"connectionId": "your-connection-id"}'
```

**Find your connection ID:** Airbyte UI → Connection → URL contains the UUID.

---

## 5. Diagnosing "Sync Succeeded but No Rows"

This is the most confusing state. Possible causes:

```
Sync succeeded, 0 rows synced
│
├── Is the source table active? (check MAX(updated_at) at source)
│   └── NO → Source stopped writing; pipeline is fine, data problem is upstream
│
├── Is the cursor field advancing?
│   └── NO → Cursor stuck; reset connection state in Airbyte
│
├── Is the watermark ahead of actual data?
│   └── YES → Airbyte cursor advanced past source data; full refresh may be needed
│
└── Was a Full Refresh run recently?
    └── YES → Airbyte may have reset the watermark; check job history
```

**Reset connection state (use with caution — triggers full reload):**
Airbyte UI → Connection → Settings → Reset connection data

---

## 6. Sync Frequency Monitoring with a Shell Script

Simple script to log sync outcomes to a file for audit:

```bash
#!/bin/bash
# monitor-airbyte.sh — run via cron or manually

CONNECTION_ID="your-connection-id"
AIRBYTE_URL="http://localhost:8001"
LOG_FILE="/var/log/airbyte-monitor.log"

response=$(curl -s -X GET "$AIRBYTE_URL/api/v1/jobs/list" \
  -H "Content-Type: application/json" \
  -d "{\"configId\": \"$CONNECTION_ID\", \"configType\": \"sync\", \"pageSize\": 1}")

status=$(echo "$response" | python3 -c "import sys,json; j=json.load(sys.stdin); print(j['jobs'][0]['job']['status'])")
rows=$(echo "$response" | python3 -c "import sys,json; j=json.load(sys.stdin); print(j['jobs'][0]['attempts'][-1].get('totalStats', {}).get('recordsCommitted', 0))")

echo "$(date -u '+%Y-%m-%dT%H:%M:%SZ') | connection=$CONNECTION_ID | status=$status | rows_committed=$rows" >> "$LOG_FILE"

if [ "$status" != "succeeded" ]; then
  echo "ALERT: Airbyte sync $status at $(date)" >&2
fi
```

Schedule with cron:
```bash
# Run every hour, 5 minutes after the sync is expected to complete
5 * * * * /path/to/monitor-airbyte.sh
```
