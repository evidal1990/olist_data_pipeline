# Ingestion Sync Strategy — Reference

## Strategy Trade-offs

**Full Refresh**
- Pro: Simple, always consistent, handles hard deletes automatically
- Con: Full table scan on every sync — expensive at scale; rewrites entire destination table

**Incremental Append**
- Pro: Efficient, low cost, no dedup logic needed
- Con: Creates duplicate rows when source records update; hard deletes are invisible

**Incremental Append + Deduped**
- Pro: Efficient + handles updates; destination maintains a deduplicated view
- Con: Requires stable primary key; soft deletes must be explicit; slightly more complex

---

## Cursor Field Selection

Prefer `updated_at` over `created_at`. If both exist, use `updated_at`.

Watch out for:
- **Nullable cursor** — exclude rows where cursor IS NULL or handle them as earliest possible date
- **Cursor not updated on every write path** — validate with `SELECT id, updated_at FROM table ORDER BY updated_at DESC LIMIT 20` after triggering an update
- **Clock skew between source replicas** — add a small lookback window (e.g., re-read last 10 minutes) to avoid missing records

---

## Supply Chain Entity Reference

| Entity | Recommended Strategy | Reasoning |
|---|---|---|
| orders | Incremental Append + Deduped | Status changes across lifecycle |
| order_items | Incremental Append | Typically insert-only |
| customers | Incremental Append + Deduped | Profile and address updates |
| products | Incremental Append + Deduped | Price, stock, description changes |
| suppliers | Incremental Append + Deduped | Contact/contract updates |
| payments | Incremental Append + Deduped | Status transitions (pending → confirmed) |
| reviews | Incremental Append | Rarely updated after creation |
| geolocation | Full Refresh | Reference data, no cursor field |

---

## Validating the Strategy After First Sync

```sql
-- Check for unexpected duplicates (Incremental Append + Deduped)
SELECT id, COUNT(*) AS cnt
FROM `project.dataset_raw.postgres__orders`
GROUP BY id
HAVING cnt > 1;

-- Verify cursor coverage (no nulls)
SELECT COUNT(*) AS total, COUNT(updated_at) AS with_cursor
FROM source_table;

-- Check last synced watermark
SELECT MAX(_airbyte_extracted_at) AS last_sync
FROM `project.dataset_raw.postgres__orders`;
```
