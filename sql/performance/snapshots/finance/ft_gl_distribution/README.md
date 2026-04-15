# FT / GL Distribution Snapshot

## Purpose
This folder is for the finance snapshot derived from the legacy FT / GL Jasper domain.

The legacy domain mixes:
- `CI_FT` as the financial-transaction fact
- `CI_FT_GL` as GL distribution detail
- optional child transaction tables such as `CI_BSEG`, `CI_ADJ`, and `CI_PAY_SEG`

## Grain problem
This domain does not have a single grain today.

It mixes:
- one row per FT
- one row per FT GL line
- optional sibling detail by FT type

That means the legacy XML cannot be converted safely until we decide the snapshot grain intentionally.

## Likely snapshot options
### Option 1
FT header snapshot

Recommended grain:
- one row per `CI_FT.FT_ID`

Use for:
- financial transaction counts and amounts
- SA/account/bill context
- FT type and GL distribution status analysis

### Option 2
FT GL distribution snapshot

Recommended grain:
- one row per `CI_FT_GL` line
- natural key: `FT_ID`, `GL_SEQ_NBR`

Use for:
- chart-of-accounts analysis
- distribution code reporting
- GL detail totals and reconciliation

## Current recommendation
Because the business need is to show FT type breakdowns inside GL accounts, this should be standardized as an FT-GL-line snapshot rather than a pure FT-header snapshot.

If the business need is "GL and FT info in one dataset", the safest design is:
- keep FT attributes repeated on each GL line
- make the snapshot grain one row per `CI_FT_GL`

If users need unduplicated FT totals, that should be a separate FT-header snapshot.

The implemented FT-GL snapshot can also be extended safely for adjustment trace reporting by adding more columns from the already-joined `CI_ADJ` row and a single ranked customer row per account.

`STATISTIC_AMOUNT` should be stored without a forced scale in the snapshot table. Source `CI_FT_GL.STATISTIC_AMOUNT` can carry fractional precision beyond cents, and forcing `NUMBER(15,2)` creates a small but real reconciliation drift at aggregate level.

Batch provenance is now sourced from the latest `CI_FT_PROC` row per `FT_ID` and persisted into the snapshot as:
- `BATCH_CD`
- `BATCH_NBR`
- `IS_LATEST_BATCH_NBR` (reserved in the current release shape; not populated by the refresh procedure)

Several raw system-control fields from `CI_FT` and `CI_FT_GL` are intentionally carried in the snapshot for traceability, but they do not need to be exposed to end users unless a real business use case exists. Examples include internal switch flags, `CHAR_TYPE_CD`, and tenant-technical division/currency fields when they are not active reporting dimensions.

The snapshot now also persists tender-report-friendly finance derivations:
- `DEBIT_AMT`
- `CREDIT_AMT`

These are derived from the sign of `GL_AMOUNT` and keep repeated JRXML-level debit/credit formulas out of downstream reports.

## Known legacy domain defects to validate
1. `CI_FT` to `CI_ADJ` joins `PARENT_ID` to `ADJ_TYPE_CD`, which is almost certainly incorrect.
2. The child joins to `CI_BSEG`, `CI_ADJ`, and `CI_PAY_SEG` do not include FT-type filters in the join condition.
3. Optional child tables are followed by `inner` joins to their lookup tables, which can drop non-matching FT types.
4. `CI_PREM.TREND_AREA_CD` is joined to `CI_TREND_AREA_L.DESCR` instead of the code column.
5. `FT_TYPE_FLG_DESC` and `GL_DISTRIB_STATUS_DESC` are hard-coded formulas instead of governed lookup-driven descriptions where available.

## Workflow
1. Run `00b_fast_preflight_validation.sql` first.
2. Use `00a_legacy_domain_preflight_validation.sql` only if you still need to test the full legacy XML join shape.
3. Decide whether the real business grain is FT or FT GL line.
4. Build the snapshot from validated SQL logic, not directly from the legacy XML.

## Domain XML
- Workspace copy: `FT_GL_DISTRIBUTION_RPT_CURR_End_User_Friendly.xml`
- Import bundle: `domains/exports/manual_imports/FT_GL_DISTRIBUTION_RPT_CURR_End_User_Friendly.xml`
- Keep both copies synchronized when the Domain changes.

## Master Guide
- Full technical guide: `07_master_technical_guide.md`
- Use it for end-to-end implementation detail, field inventory, QA results, replication steps, and debugging guidance.

## Implemented snapshot
- `01_create_snapshot_table.sql`
- `01a_alter_existing_snapshot_table.sql`
- `02_refresh_snapshot_procedure.sql`
- `03_schedule_snapshot_job.sql`
- `04_validation_queries.sql`
- `05_intensive_qa_queries.sql`
- `06_qa_results_template.md`
- `07_master_technical_guide.md`
- `FT_GL_DISTRIBUTION_RPT_CURR_End_User_Friendly.xml`
