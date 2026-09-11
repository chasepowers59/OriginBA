# Unbilled Revenue SQL Pack

Purpose:
- Produce a high-performance daily unbilled revenue estimate snapshot for C2M.
- Keep Jasper runtime fast by moving heavy estimation logic into scheduled SQL.

Business definition implemented:
- Unbilled window per SA: from last billed segment end date to current business date.
- Estimated unbilled revenue:
  - Usage-based estimated charges (unbilled quantity * historical unit rate)
  - Plus estimated non-usage charges (historical FT_OTHER_AMT daily run-rate * unbilled days)
  - Plus estimated tax (historical SA tax ratio applied to estimated subtotal)

Outputs:
- Snapshot table: `CISADM.C1_BI_UNBILLED_REV_SNAP`
- Grain: `AS_OF_DT + SA_ID`

Files:
1. `00_create_snapshot_table.sql`
- One-time DDL (table + PK + performance indexes).

2. `01_refresh_snapshot_estimate.sql`
- Daily refresh SQL with bind parameters:
  - `:P_AS_OF_DATE` (DATE, default `SYSDATE`)
  - `:P_LOOKBACK_DAYS` (NUMBER, default `120`)
  - `:P_SA_STATUS_FLG` (CHAR, default `'20'`)

3. `02_validation_queries.sql`
- Read-only quality checks and reconciliation sanity.

Operational recommendations:
- Run refresh nightly after usage ingestion and billing/FT posting windows complete.
- Keep `LOOKBACK_DAYS` between 90 and 180 for stability vs recency balance.
- Partition snapshot by `AS_OF_DT` (already in DDL) and purge older partitions per retention policy.

Known estimation caveats:
- This is an estimate model, not a replacement for C2M bill calculation engine output.
- Effective for revenue accrual trending, management reporting, and operational monitoring.
