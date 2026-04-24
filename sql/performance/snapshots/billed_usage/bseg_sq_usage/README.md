# BSEG SQ Usage Snapshot

## Purpose
This folder is for the determinant-grain billed-usage snapshot built from completed bill segments and `CI_BSEG_SQ`.

This snapshot exists because `SA_TYPE` does not map cleanly to one unit family in this client data, so quantity reporting by service type from the segment-level snapshot can be misleading.

## Grain
Recommended grain:
- one row per billed-usage determinant key on a completed bill segment
- natural key: `BSEG_ID`, `UOM_CD`, `TOU_CD`, `SQI_CD`

If a bill segment has multiple `CI_BSEG_SQ` rows with the same determinant key, this snapshot aggregates them together intentionally so quantity remains additive at the determinant grain.

## Use for
- billed usage by `UOM_CD`
- billed usage by `UOM_CD` + `TOU_CD`
- billed usage by `SQI_CD`
- determinant-level usage analysis by account, service type, bill cycle, or customer class
- identifying which service types mix multiple unit families

## Do not use for
- additive billed dollars by determinant
- segment-level billed-amount reconciliation
- charge allocation reporting

The allocation feasibility test showed that billed amount is not safely allocable to determinant grain across the full population:
- many completed bill segments have `CI_BSEG_CALC` header amounts with no matching `CI_BSEG_CALC_LN` parity
- many determinant keys are `SQ_ONLY`
- some billed charge lines are `CALC_ONLY`

That means determinant-level dollars should come from a separate calc-line artifact, not from this usage snapshot.

## Workflow
1. Run `sql/performance/billed_usage/validation/10_amount_allocation_feasibility.sql` if you need to re-check why dollars are excluded.
2. Build and validate `BSEG_SQ_USAGE_RPT_CURR` for quantity analysis.
3. Keep `BSEG_BILLED_USAGE_RPT_CURR` as the segment-level billed-dollar source.

## Domain XML
- Workspace copy: `BSEG_SQ_USAGE_RPT_CURR_End_User_Friendly.xml`
- Import bundle: `domains/exports/manual_imports/BSEG_SQ_USAGE_RPT_CURR_End_User_Friendly.xml`
- Keep both copies synchronized when the Domain changes.

## Master Guide
- Full technical guide: `08_master_technical_guide.md`
- Use it for end-to-end implementation detail, field inventory, QA results, replication steps, and debugging guidance.

## Implemented snapshot
- `01_create_snapshot_table.sql`
- `02_refresh_snapshot_procedure.sql`
- `02a_full_history_refresh_procedure.sql`
- `03_schedule_snapshot_job.sql`
- `04_validation_queries.sql`
- `05_bseg_determinant_trace.sql`
- `06_intensive_qa_queries.sql`
- `07_qa_results_template.md`
- `08_master_technical_guide.md`
- `09_refresh_strategy_diagnostics.sql`
- `10_fast_before_after_validation.sql`
- `11_rolling_refresh_candidate_procedure.sql`
- `BSEG_SQ_USAGE_RPT_CURR_End_User_Friendly.xml`

## Rolling-window candidate status
- The active procedure was updated on `2026-04-24` to rolling `12-month` maintenance keyed on `BILL_DT`.
- `02a_full_history_refresh_procedure.sql` preserves the original full-history `TRUNCATE + INSERT` version explicitly for first-time deployment into a new database.
- `11_rolling_refresh_candidate_procedure.sql` remains as the original promotion scaffold used for the cutover evidence.
- Validate with:
  - `09_refresh_strategy_diagnostics.sql`
  - `10_fast_before_after_validation.sql`

Rolling maintenance behavior:
- delete only rows where `BILL_DT >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12)`
- reload only that same `12-month` billing slice
- keep older history in place

## Current validation status
- Read-only validation was re-run on `2026-04-24`.
- Recent bill creation did not land into bill periods older than `12` months in the reviewed `30`, `90`, and `180` day slices.
- Rolling `12-month` monthly parity was exact against current raw-source determinant counts and additive totals.
- Whole-table parity was exact for:
  - row count
  - `TOTAL_BILL_SQ`
  - `TOTAL_INIT_SQ`
- Duplicate determinant natural keys were not present.
- Controlled cutover was executed on `2026-04-24` after the segment-level billing snapshot was promoted and validated.
- AFTER QA confirmed:
  - preserved-history rows older than the rolling window remained intact
  - rolling `12-month` monthly parity remained exact
  - whole-table totals remained exact
  - duplicate determinant natural keys remained absent
- Current status:
  - this snapshot now runs on the validated rolling-window procedure
  - it was promoted second, after the billed-usage header snapshot

Reference:
- `sql/performance/snapshots/docs/bseg_rolling_window_validation_2026-04-24.md`
