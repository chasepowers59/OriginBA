# Account Debt Snapshot

This folder is for the debt-management account snapshot built from governed arrears logic in `CISADM.CI_FT`.

## Purpose

`CISADM.ACCT_DEBT_RPT_CURR` is the standardized debt-management snapshot for current account-level debt exposure.

It is designed for ad hoc reporting where users need one row per account with:
- trusted outstanding debt from financial transactions
- aging buckets from `ARS_DT`
- core debt-management account and customer context
- lightweight latest collections and write-off process context

## Grain

One row per `ACCT_ID` with positive governed arrears balance.

Natural key:
- `ACCT_ID`

## Driving truth

Debt truth comes from `CISADM.CI_FT` joined to active service agreements:
- `FREEZE_SW = 'Y'`
- `NOT_IN_ARS_SW = 'N'`
- `FT_TYPE_FLG NOT IN ('PS', 'PX')`
- `ARS_DT IS NOT NULL`
- `CI_SA.SA_STATUS_FLG = '20'`

This keeps the snapshot focused on current relevant debt rather than all historical process rows.

## What is included

- trusted total debt and aging buckets at account grain
- arrears FT and SA counts
- oldest and most recent arrears dates
- collection class and credit-review context
- primary customer row when available
- active SA count
- debt-class profile across active SAs
- last bill date
- latest collection-process context from `CI_COLL_PROC`
- latest write-off context from `C1_BI_WOPROC_VW`
- collection-agency reference count linked to write-off processes

## What is intentionally excluded

- row-per-FT debt detail
- row-per-collection-process detail
- row-per-write-off-process detail
- payment arrangement data

Those belong in separate lower-grain or process-specific snapshots.

## Key design rule

`TOTAL_DEBT` is the trusted additive measure in this snapshot.

Process fields such as latest collection or write-off status are descriptive account overlays, not replacement debt truth.

`SOLE_DEBT_CL_CD` / `SOLE_DEBT_CL_DESC` are only populated when the account has exactly one active-SA debt class in scope.

The refresh is intentionally split into two phases:
- base account debt fact load
- post-load enrichment merges for customer, bill, collections, and write-off context

The base load intentionally avoids `INSERT /*+ APPEND */` because the `CI_FT`
scan is the slowest part of the refresh and direct-path insert keeps a stronger
lock on the snapshot table while that scan runs.

## Recommended use

- account outreach and prioritization
- aging dashboards
- collections segmentation
- identifying accounts in debt with current collections or write-off involvement

## Do not use for

- collection-process workflow detail
- write-off effectiveness analysis
- FT-level reconciliation or row tracing

Use separate process snapshots for those subjects.

## Domain XML
- Workspace copy: `ACCT_DEBT_RPT_CURR_End_User_Friendly.xml`
- Import bundle: `domains/exports/manual_imports/ACCT_DEBT_RPT_CURR_End_User_Friendly.xml`
- Keep both copies synchronized when the Domain changes.

## Implemented snapshot

- `01_create_snapshot_table.sql`
- `02_refresh_snapshot_procedure.sql`
- `03_schedule_snapshot_job.sql`
- `04_validation_queries.sql`
- `05_sql_developer_perf_checks.sql`
- `ACCT_DEBT_RPT_CURR_End_User_Friendly.xml`
