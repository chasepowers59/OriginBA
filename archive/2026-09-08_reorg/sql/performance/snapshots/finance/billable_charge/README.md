# Billable Charge Snapshot

This folder is for the finance billable-charge snapshot built from `CISADM.CI_BILL_CHG` and `CISADM.CI_B_CHG_LINE` with service-agreement and account context aligned to the Standard Offering `Billable_Charge___Domain` join graph.

## Purpose

`CISADM.BILLABLE_CHARGE_RPT_CURR` is the standardized finance snapshot for billable charge line reporting.

It is designed for ad hoc reporting where users need one safe row per billable charge line with:
- charge header dates, status, and template context
- line amount, description, and distribution attributes
- service-agreement and account context
- primary customer name

## Grain

One row per `BILLABLE_CHG_ID` + `LINE_SEQ`.

Natural key:
- `BILLABLE_CHG_ID`
- `LINE_SEQ`

## Why this grain was chosen

The legacy `Billable_Charge___Domain` drives from `CI_SA`, joins `CI_BILL_CHG`, and then joins `CI_B_CHG_LINE`.

Keeping billable charge line as the snapshot grain preserves:
- one row per charge line without header duplication
- safe additive sums on `CHARGE_AMT`
- parity with Standard Offering billable-charge Ad Hoc views

## Driving tables

- `CISADM.CI_B_CHG_LINE`
- `CISADM.CI_BILL_CHG`
- `CISADM.CI_SA`
- `CISADM.CI_ACCT`
- `CISADM.CI_ACCT_PER`
- `CISADM.CI_PER_NAME`

Lookup and presentation tables:
- `CISADM.CI_SA_TYPE`
- `CISADM.CI_SA_TYPE_L`
- `CISADM.CI_LOOKUP_VAL_L`
- `CISADM.CI_CIS_DIVISION_L`
- `CISADM.CI_BILL_CYC_L`
- `CISADM.CI_COLL_CL_L`
- `CISADM.CI_CUST_CL_L`
- `CISADM.CI_BUD_PLAN_L`

## What is included

- billable charge header fields (`START_DT`, `END_DT`, `BILLABLE_CHG_STAT`, `BILL_CHG_TMPLT_CD`)
- billable charge line fields (`CHARGE_AMT`, `DESCR_ON_BILL`, `DST_ID`, `SHOW_ON_BILL_SW`)
- SA status, type, and division descriptions
- account class, bill cycle, and customer name

## What is intentionally excluded

- row-per-financial-transaction detail
- billed bill-segment detail
- account-level debt truth

Those belong in separate finance or debt-management snapshots.

## Key design rules

- `CHARGE_AMT` is the trusted additive measure in this snapshot.
- Charge header context is repeated on each line row by design so line-level reporting stays self-contained.
- Customer and account joins follow the Standard Offering main-customer / primary-name pattern.

## Rolling refresh window

The operational procedure keeps a `6-month` rolling scope on charge dates:
- retain rows when `START_DT` or `END_DT` falls inside the window
- retain open charges with no `END_DT`

## Recommended use

- billable charge line amount reporting
- charge status and template workload
- SA/account charge context for finance operations

## Do not use for

- billed bill-segment reconciliation
- account-level debt exposure
- payment or adjustment tracing

Use governed billed-usage, FT, or debt-management snapshots for those subjects.

## Workflow

1. Create the snapshot table with `01_create_snapshot_table.sql`.
2. Run the one-time baseline load with `02a_full_history_refresh_procedure.sql`.
3. Deploy the operational rolling refresh with `02_refresh_snapshot_procedure.sql`.
4. Validate row safety and description coverage with `04_validation_queries.sql`.

## Implemented snapshot

- `01_create_snapshot_table.sql`
- `02a_full_history_refresh_procedure.sql`
- `02_refresh_snapshot_procedure.sql`
- `04_validation_queries.sql`
