# Collection Process Snapshot

This folder is for the debt-management collection-process snapshot built from `CISADM.CI_COLL_PROC` with pre-aggregated event context from `CISADM.CI_COLL_EVT`.

## Purpose

`CISADM.COLL_PROC_RPT_CURR` is the standardized debt-management snapshot for collection-process reporting.

It is designed for ad hoc reporting where users need one safe row per collection process with:
- process status and template context
- account and customer context
- process arrears-at-trigger values
- event counts and timing
- current / next collection event context without duplicating the process row

## Grain

One row per `COLL_PROC_ID`.

Natural key:
- `COLL_PROC_ID`

## Why this grain was chosen

The legacy domain mixes:
- `CI_COLL_PROC` as process header
- `CI_COLL_EVT` as process child detail
- account and customer joins

If `CI_COLL_EVT` is joined directly, one collection process repeats across multiple event rows.

That makes counts and process-level measures unsafe unless event rows are aggregated first.

## What is included

- process header fields from `CI_COLL_PROC`
- account-level context from `CI_ACCT`
- primary customer name when available
- collection class, customer class, bill cycle, and account-management descriptions
- event counts, first/last trigger dates, first/last completion dates
- next open event context
- latest event context

## What is intentionally excluded

- one row per event
- CC child detail
- severance detail rows
- debt truth from `CI_FT`

Those belong in separate snapshots or the account-debt snapshot.

## Key design rule

This is a process-workflow snapshot, not a debt-balance snapshot.

`ARS_AMT` here is process context from `CI_COLL_PROC`, not the same thing as account-level total debt truth from `ACCT_DEBT_RPT_CURR`.

## End-user guidance

Use this snapshot for:
- monitoring open collection processes
- template/status workloads
- identifying next event type by process
- queue and operations reviews

Do not use it to answer:
- total account debt
- debt aging by account

Use `ACCT_DEBT_RPT_CURR` for those questions.

## Domain XML
- Workspace copy: `COLL_PROC_RPT_CURR_End_User_Friendly.xml`
- Import bundle: `domains/exports/manual_imports/COLL_PROC_RPT_CURR_End_User_Friendly.xml`
- Keep both copies synchronized when the Domain changes.

## Implemented snapshot

- `01_create_snapshot_table.sql`
- `02_refresh_snapshot_procedure.sql`
- `03_schedule_snapshot_job.sql`
- `04_validation_queries.sql`
- `COLL_PROC_RPT_CURR_End_User_Friendly.xml`
