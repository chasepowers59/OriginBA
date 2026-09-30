# SA Aged Balance Snapshot

This folder is for the debt-management service-agreement aged-balance snapshot built from governed arrears logic in `CISADM.CI_FT`, replacing the mixed snapshot-table pattern in the Standard Offering `SA_Snapshot___Aged_Balance___Domain`.

## Purpose

`CISADM.SA_AGED_BAL_RPT_CURR` is the standardized debt-management snapshot for current SA-level debt exposure.

It is designed for ad hoc reporting where users need one row per service agreement with:
- trusted outstanding debt from financial transactions
- aging buckets from `ARS_DT`
- SA, account, customer, and premise context
- debt-class profile from `CI_SA_TYPE`

## Grain

One row per `SA_ID` with positive governed arrears balance.

Natural key:
- `SA_ID`

## Driving truth

Debt truth comes from `CISADM.CI_FT` joined to service agreements:
- `FREEZE_SW = 'Y'`
- `NOT_IN_ARS_SW = 'N'`
- `FT_TYPE_FLG NOT IN ('PS', 'PX')`
- `ARS_DT IS NOT NULL`

This mirrors `ACCT_DEBT_RPT_CURR` arrears logic, but keeps debt at service-agreement grain instead of rolling it up to account grain.

## What is included

- trusted total debt and aging buckets at SA grain
- arrears FT count
- oldest and most recent arrears dates
- SA status, type, and debt-class context
- account class and bill-cycle context
- primary customer name
- premise address context when `CHAR_PREM_ID` is populated

## What is intentionally excluded

- row-per-FT debt detail
- CMS snapshot-table history (`CMS_SA_SNAPSHOT`)
- account-level debt rollups
- collection-process or write-off process detail

Those belong in separate lower-grain or process-specific snapshots.

## Key design rule

`TOTAL_DEBT` is the trusted additive measure in this snapshot.

The refresh intentionally avoids `INSERT /*+ APPEND */` because the `CI_FT` scan is the slowest part of the refresh and direct-path insert keeps a stronger lock on the snapshot table while that scan runs.

## Population filters

### Full-history baseline (`02a`)

- active service agreements only (`SA_STATUS_FLG = '20'`)
- positive governed arrears balance

### Operational refresh (`02`)

- active service agreements with positive governed arrears
- recently ended service agreements with positive governed arrears when `END_DT` falls inside the `6-month` rolling window

## Recommended use

- SA outreach and prioritization
- aging dashboards by service agreement
- premise-linked debt segmentation
- replacement for current-state SA aged-balance Ad Hoc views

## Do not use for

- account-level debt totals across all SAs
- collection-process workflow detail
- write-off effectiveness analysis
- historical CMS snapshot comparisons

Use `ACCT_DEBT_RPT_CURR`, `COLL_PROC_RPT_CURR`, or `WO_PROC_RPT_CURR` for those subjects.

## Workflow

1. Create the snapshot table with `01_create_snapshot_table.sql`.
2. Run the one-time baseline load with `02a_full_history_refresh_procedure.sql`.
3. Deploy the operational refresh with `02_refresh_snapshot_procedure.sql`.
4. Validate row safety, debt reconciliation, and description coverage with `04_validation_queries.sql`.

## Implemented snapshot

- `01_create_snapshot_table.sql`
- `02a_full_history_refresh_procedure.sql`
- `02_refresh_snapshot_procedure.sql`
- `04_validation_queries.sql`
