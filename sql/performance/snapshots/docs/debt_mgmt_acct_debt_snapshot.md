# Debt Management Account Debt Snapshot

## Purpose
`CISADM.ACCT_DEBT_RPT_CURR` is the governed debt-management snapshot for current account-level debt exposure.

It is the right artifact when the business question is:
- how much debt exists by account
- how debt is distributed across aging buckets
- which collection classes or debt classes carry the most exposure
- which accounts have debt plus current collections or write-off context

## Grain
One row per `ACCT_ID` with positive governed arrears balance.

Natural key:
- `ACCT_ID`

## Driving truth
Debt truth comes from governed arrears logic in `CISADM.CI_FT`, constrained to active service agreements and in-scope arrears rows.

That means this snapshot is an account-debt fact, not a process fact.

## What is included
- trusted `TOTAL_DEBT`
- aging buckets
- arrears dates
- account and customer context
- collection class and credit-review context
- active SA and arrears FT counts
- latest collection-process overlay
- latest write-off overlay

## What is intentionally excluded
- one row per FT
- one row per collection process
- one row per write-off process
- payment arrangement detail

Those belong in separate lower-grain or process-specific artifacts.

## Key design rule
`TOTAL_DEBT` is the trusted additive measure.

Latest collection or write-off fields are descriptive overlays. They should not replace account-level debt truth.

## XML artifact
Importable Domain XML:
- `domains/exports/manual_imports/ACCT_DEBT_RPT_CURR_End_User_Friendly.xml`

Companion XML inventory:
- `sql/performance/snapshots/docs/snapshot_xml_inventory.md`

## SQL workspace
- `sql/performance/snapshots/debt_mgmt/acct_debt/`

## Ad hoc guide
- `docs/debt_mgmt_acct_debt_adhoc_recipes.md`

## SQL Developer runbook
For exact SQL Developer steps to inspect the table, view the current procedure, and validate the scheduler job, use:
- `sql/performance/snapshots/docs/snapshot_sqldeveloper_runbook.md` under `ACCT_DEBT_RPT_CURR`

## Business summary
This table answers the question:

"At the account level, how much collectible debt exists right now, how old is it, and what collections or write-off context surrounds it?"
