# Write-Off Process Snapshot

This folder is for the debt-management write-off process snapshot built from `CISADM.CI_WO_PROC` with pre-aggregated event context from `CISADM.CI_WO_EVT` and optional BI enrichment from `CISADM.C1_BI_WOPROC_VW`.

## Purpose

`CISADM.WO_PROC_RPT_CURR` is the standardized debt-management snapshot for write-off process reporting.

It is designed for ad hoc reporting where users need one safe row per write-off process with:
- process status, template, and control context
- account and customer context
- optional BI exposure and duration fields from `C1_BI_WOPROC_VW`
- pre-aggregated write-off event counts and timing
- active / inactive write-off SA amount rollups from `CI_WO_PROC_SA`

## Grain

One row per `WO_PROC_ID`.

Natural key:
- `WO_PROC_ID`

## Why this grain was chosen

The legacy `Write_Off_Process___Domain` drives from `CI_WO_PROC` and joins `CI_WO_EVT` directly.

If `CI_WO_EVT` is joined without aggregation, one write-off process repeats across multiple event rows.

That makes counts and process-level measures unsafe unless event rows are aggregated first.

## Driving tables

- `CISADM.CI_WO_PROC`
- `CISADM.CI_WO_EVT`
- `CISADM.CI_WO_PROC_SA`
- `CISADM.CI_ACCT`
- `CISADM.CI_ACCT_PER`
- `CISADM.CI_PER_NAME`

Optional BI enrichment:
- `CISADM.C1_BI_WOPROC_VW`

Lookup and presentation tables:
- `CISADM.CI_WO_PROC_TMPL_L`
- `CISADM.CI_WO_CNTL_L`
- `CISADM.CI_LOOKUP_VAL_L`
- `CISADM.CI_WO_EVT_TYP_L`
- `CISADM.CI_BILL_CYC_L`
- `CISADM.CI_COLL_CL_L`
- `CISADM.CI_CUST_CL_L`
- `CISADM.CI_ACCT_MGMT_GR_L`
- `CISADM.CI_BUD_PLAN_L`

## What is included

- process header fields from `CI_WO_PROC`
- optional BI fields when the tenant view is populated:
  - `ARS_AT_START`
  - `ARS_AT_END`
  - `ARS_DIFF`
  - `UNCOLL_PROC_DUR`
  - `UNCOLL_PROC_STAT_FLG`
- account-level context from `CI_ACCT`
- primary customer name when available
- event counts, first/last trigger dates, first/last completion dates
- next open event context
- latest event context
- active / inactive write-off SA amount rollups

## What is intentionally excluded

- one row per write-off event
- one row per write-off SA
- payment recovery estimates
- account-level debt truth from `CI_FT`

Those belong in separate snapshots or analytics SQL packs.

## Key design rules

- This is a process-workflow snapshot, not a debt-balance snapshot.
- `C1_BI_WOPROC_VW` is joined only as an optional `LEFT JOIN` when the tenant view exists. Validate population with `00a_config_discovery_validation.sql` before production rollout.
- `WO_SA_STAT_FLG` active / inactive split uses `10` / `20`. Validate exact lookup semantics in `CI_LOOKUP_VAL_L` before final KPI governance.
- `ARS_AT_START` and related BI measures are descriptive process overlays, not replacement debt truth.

## Rolling refresh window

The operational procedure keeps a `6-month` rolling scope on process dates:
- retain processes created inside the window
- retain open processes with no completion date
- retain recently completed processes when `WO_PROC_COMPL_DT` falls inside the window

## Recommended use

- monitoring open write-off processes
- template/status workloads
- identifying next write-off event type by process
- write-off exposure and duration reporting when `C1_BI_WOPROC_VW` is populated

## Do not use for

- total account debt
- debt aging by account or SA
- payment recovery effectiveness without the dedicated write-off analytics SQL pack

Use `ACCT_DEBT_RPT_CURR`, `SA_AGED_BAL_RPT_CURR`, or `sql/performance/write_off/` for those subjects.

## Workflow

1. Create the snapshot table with `01_create_snapshot_table.sql`.
2. Run the one-time baseline load with `02a_full_history_refresh_procedure.sql`.
3. Deploy the operational rolling refresh with `02_refresh_snapshot_procedure.sql`.
4. Validate row safety, event reconciliation, and description coverage with `04_validation_queries.sql`.

## Implemented snapshot

- `01_create_snapshot_table.sql`
- `02a_full_history_refresh_procedure.sql`
- `02_refresh_snapshot_procedure.sql`
- `04_validation_queries.sql`
