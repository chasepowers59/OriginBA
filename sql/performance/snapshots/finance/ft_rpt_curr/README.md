# FT Header Snapshot

## Purpose
This folder is for the FT-header snapshot built from `CISADM.CI_FT`.

`CISADM.FT_RPT_CURR` is the standardized finance snapshot for one-row-per-FT reporting with account, service agreement, bill-segment, adjustment, and payment context flattened onto the transaction.

## Grain
One row per `CI_FT.FT_ID`.

Natural key:
- `FT_ID`

## Driving tables
- `CISADM.CI_FT`
- `CISADM.CI_SA`
- `CISADM.CI_ACCT`

Optional FT-type-specific child detail:
- `CISADM.CI_BSEG`
- `CISADM.CI_ADJ`
- `CISADM.CI_PAY_SEG`

Lookup and presentation tables:
- `CISADM.SC_USER`
- `CISADM.CI_LOOKUP_VAL_L`
- `CISADM.CI_SA_TYPE_L`
- `CISADM.CI_ADJ_TYPE_L`
- `CISADM.CI_CUST_CL_L`
- `CISADM.CI_COLL_CL_L`
- `CISADM.CI_BILL_CYC_L`
- `CISADM.CI_ACCT_MGMT_GR_L`

## What it is for
- FT counts and FT amounts
- FT type mix and GL distribution status analysis
- account, SA, service type, and bill-cycle slicing
- adjustment trace views
- payment-segment-linked FT views
- bill-segment-linked FT views

## What it is not for
- GL line analysis
- GL account or distribution-code reconciliation
- any use case that needs one row per `CI_FT_GL`

Use `snapshots/finance/ft_gl_distribution/` for those subjects.

## Current implementation notes
- The load uses `TRUNCATE` and a full reload, matching the supplied implementation.
- FT and GL status descriptions are derived with `CASE` expressions.
- Customer class, collection class, bill cycle, and account-management-group descriptions are resolved into the snapshot for business-facing ad hoc use.
- Child joins are gated by `FT_TYPE_FLG` so adjustment, bill-segment, and payment fields only populate for the matching FT families.
- The supplied DDL keeps several ID columns at `VARCHAR2(30)`. Repo metadata for source tables shows some upstream IDs are wider than 30, so widen those columns before rollout if your environment contains full-width source keys.

## Workflow
1. Create the snapshot table with `01_create_snapshot_table.sql`.
2. For an existing deployed table, run `01a_alter_existing_snapshot_table.sql`.
3. Create the refresh procedure with `02_refresh_snapshot_procedure.sql`.
4. Optionally schedule the refresh with `03_schedule_snapshot_job.sql`.
5. Validate row safety and description coverage with `04_validation_queries.sql`.

## Domain XML
- Workspace copy: `FT_RPT_CURR_End_User_Friendly.xml`
- Import bundle: `domains/exports/manual_imports/FT_RPT_CURR_End_User_Friendly.xml`
- Keep both copies synchronized when the Domain changes.

## Master Guide
- Full technical guide: `08_master_technical_guide.md`
- Use it for end-to-end implementation history, field inventory, QA results, replication steps, and debugging guidance.

## Implemented snapshot
- `01_create_snapshot_table.sql`
- `01a_alter_existing_snapshot_table.sql`
- `02_refresh_snapshot_procedure.sql`
- `03_schedule_snapshot_job.sql`
- `04_validation_queries.sql`
- `05_materialized_view_cutover_runbook.md`
- `06_intensive_qa_queries.sql`
- `07_qa_results_template.md`
- `08_master_technical_guide.md`
- `FT_RPT_CURR_End_User_Friendly.xml`
