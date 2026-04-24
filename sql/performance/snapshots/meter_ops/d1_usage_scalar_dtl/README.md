# D1 Usage Scalar Detail Snapshot

## Purpose
This folder is for the scalar-detail usage snapshot built from `CISADM.D1_USAGE_SCALAR_DTL`.

It exists because quantity by `UOM / TOU / SQI`, customer class, premise, and measuring component is a different fact than a usage header and should not be forced into `D1_USAGE_RPT_CURR`.

## Grain
One row per scalar detail line in `CISADM.D1_USAGE_SCALAR_DTL`.

Natural key:
- `D1_USAGE_ID`
- `SEQ_NUM`

Current validation note:
- in the connected test environment, source data contains `48` duplicate
  `(D1_USAGE_ID, SEQ_NUM)` pairs
- the snapshot mirrors those same duplicates, so the procedure is source-
  consistent but the documented natural key is not a guaranteed unique key in
  this environment

## Use for
- quantity and final quantity analysis by `UOM / TOU / SQI`
- customer class, service type, and premise consumption reporting
- measuring component and service point usage breakdowns
- raw vs. final usage comparison
- billing-linked scalar trace analysis

## Do not use for
- one-row-per-usage transaction counts
- usage-process monitoring without detail context

Use `D1_USAGE_RPT_CURR` for the header/process view.

## Key design rules
1. Drive from `D1_USAGE_SCALAR_DTL` joined to a rolling-window `D1_USAGE` batch.
2. Keep one row per scalar detail sequence.
3. Bring usage-header, subscription, billing, SA/account/customer, and premise context onto each scalar row.
4. Keep the `C1_USAGE` bridge optional and limited to the canonical billing path (`D1_USAGE.USG_EXT_ID -> C1_USAGE.USAGE_ID`, `BO_STATUS_CD = 'BD-PROC'`).
5. Run one full-history baseline load first, then switch nightly processing to a rolling 12-month refresh.
6. Load the nightly rolling window in 3-month batches so loop overhead drops without forcing one giant insert.
7. Delete only the current rolling-window scalar population by parent `D1_USAGE_ID` so older history stays in place.

## Operational note
The rolling refresh assumes the snapshot already has its historical baseline.

Deployment sequence:
1. Deploy and run `02a_full_history_refresh_procedure.sql` first so `D1_USAGE_SCALAR_DTL_RPT_CURR` is populated with all required historical data.
2. After that baseline load succeeds, deploy `02_refresh_snapshot_procedure.sql` so nightly refreshes switch to the rolling 12-month pattern.

If `D1_USAGE_SCALAR_DTL_RPT_CURR` is empty and you deploy the rolling procedure immediately, it will load only the last 12 months and older history will be missing from the snapshot.

Validated cutover note:
- on `2026-04-20`, before/after validation confirmed that the rolling 12-month nightly procedure preserved the existing scalar snapshot row counts and additive usage totals while keeping historical rows in place
- on `2026-04-24`, follow-up review confirmed rolling-window quantity parity is
  still exact, but duplicate `(D1_USAGE_ID, SEQ_NUM)` pairs remain present in
  both source and snapshot and need separate grain-definition review

## Domain XML
- Workspace copy: `D1_USAGE_SCALAR_DTL_RPT_CURR_End_User_Friendly.xml`
- Import bundle: `domains/exports/manual_imports/D1_USAGE_SCALAR_DTL_RPT_CURR_End_User_Friendly.xml`
- Keep both copies synchronized when the Domain changes.

## Master Guide
- Full technical guide: `07_master_technical_guide.md`
- Use it for final design, refresh behavior, QA evidence, and deployment/debugging guidance.

## Implemented snapshot
- `01_create_snapshot_table.sql`
- `02_refresh_snapshot_procedure.sql`
- `02a_full_history_refresh_procedure.sql`
- `03_schedule_snapshot_job.sql`
- `04_validation_queries.sql`
- `05_intensive_qa_queries.sql`
- `06_qa_results_template.md`
- `07_master_technical_guide.md`
- `08_performance_diagnostics.sql`
- `09_optimization_notes.md`
- `10_before_after_validation.sql`
- `D1_USAGE_SCALAR_DTL_RPT_CURR_End_User_Friendly.xml`
