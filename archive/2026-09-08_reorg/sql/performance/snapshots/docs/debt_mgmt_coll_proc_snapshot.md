# Debt Management Collection Process Snapshot

## Purpose
`CISADM.COLL_PROC_RPT_CURR` is the governed debt-management snapshot for collection-process workflow reporting.

It is the right artifact when the business question is:
- how many collection processes are open
- what statuses and templates are active
- what the next event or latest event looks like
- which accounts are flowing through collections operations

## Grain
One row per `COLL_PROC_ID`.

Natural key:
- `COLL_PROC_ID`

## Driving truth
The driving header is `CISADM.CI_COLL_PROC`.

Event detail from `CI_COLL_EVT` is aggregated before joining so the process row stays safe.

## What is included
- process status and template context
- account and customer context
- process arrears-at-trigger values
- event counts and event timing
- latest event context
- next open event context

## What is intentionally excluded
- row-per-event detail
- full debt truth from `CI_FT`
- severance or agency child detail

Those belong in separate snapshots or in `ACCT_DEBT_RPT_CURR`.

## Key design rule
This is a process-workflow snapshot, not an account-debt snapshot.

`ARS_AMT` here is process context, not replacement debt truth.

## XML artifact
Importable Domain XML:
- `domains/exports/manual_imports/COLL_PROC_RPT_CURR_End_User_Friendly.xml`

Companion XML inventory:
- `sql/performance/snapshots/docs/snapshot_xml_inventory.md`

## SQL workspace
- `sql/performance/snapshots/debt_mgmt/coll_proc/`

## Ad hoc guide
- `docs/debt_mgmt_coll_proc_adhoc_recipes.md`

## SQL Developer runbook
For exact SQL Developer steps to inspect the table, view the current procedure, and validate the scheduler job, use:
- `sql/performance/snapshots/docs/snapshot_sqldeveloper_runbook.md` under `COLL_PROC_RPT_CURR`

## Business summary
This table answers the question:

"For each collections process, what status is it in, what events have happened, what event is next, and which account does it belong to?"
