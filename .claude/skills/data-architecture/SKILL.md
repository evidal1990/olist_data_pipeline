---
name: data-architecture
description: Use when designing or reviewing data ingestion pipelines — choosing sync strategies, evaluating source tables for incremental readiness, or designing a raw layer in a data warehouse. Use when deciding between Full Refresh, Incremental Append, or Incremental Append+Deduped, or when assessing partitioning and clustering for BigQuery raw tables.
---

# Data Architecture — Ingestion

## Overview

Three decisions determine whether an ingestion pipeline is robust:
1. **Sync strategy** — how records move from source to destination
2. **Source readiness** — whether the source supports the chosen strategy
3. **Raw layer design** — how data lands in the warehouse

See supporting files for detailed guidance:
- [ingestion-sync-strategy.md](ingestion-sync-strategy.md)
- [source-readiness-assessment.md](source-readiness-assessment.md)
- [raw-layer-design.md](raw-layer-design.md)

---

## Sync Strategy — Quick Decision

```
Has reliable cursor field (updated_at)?
├── NO  → Full Refresh
└── YES → Has stable primary key?
          ├── NO  → Incremental Append
          └── YES → Records get updated/deleted?
                    ├── NO  → Incremental Append
                    └── YES → Incremental Append + Deduped
```

| Strategy | Cost | Use when |
|---|---|---|
| Full Refresh | High | No cursor; small/reference tables |
| Incremental Append | Low | Insert-only (events, logs) |
| Incremental Append + Deduped | Medium | Entities that change (orders, customers) |

---

## Source Readiness — Checklist

Before configuring incremental sync, verify:

- [ ] Primary key exists and is stable
- [ ] `updated_at` is populated and updated on every write path
- [ ] No nullable cursor field
- [ ] Soft deletes used (not hard deletes), or gap is accepted
- [ ] Data volume is known (drives sync frequency decision)

If any item fails → fall back to Full Refresh or fix the source first.

---

## Raw Layer Design — Key Rules

**Naming:** `<dataset>_raw.<source>__<table>` (e.g., `supply_chain_raw.postgres__orders`)

**Partitioning:** by `_airbyte_extracted_at` (ingestion date) for most tables; by cursor field if queries filter on it.

**Clustering:** by primary key for Deduped tables; by most-queried filter column otherwise.

**Never transform at raw layer.** Raw = exact copy of source, including `_airbyte_*` metadata columns.

---

## Common Mistakes

| Mistake | Fix |
|---|---|
| Incremental Append on a table where rows update | Switch to Deduped or assess update pattern first |
| Full Refresh on a large table at high frequency | Evaluate incremental feasibility; increase interval |
| No partitioning on tables > 1GB | Add partition by ingestion date |
| Ignoring hard deletes in incremental | Add `deleted_at` soft-delete or document the gap |
| Cursor field that doesn't update on every write | Validate with `SELECT MAX(updated_at)` after each write path |
