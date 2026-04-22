# D1 Final Measurement Snapshot

## Purpose
This folder contains the snapshot build assets for `CISADM.D1_MSRMT_RPT_CURR`.

The snapshot preserves final processed measurement grain so measurement reporting does not rely on fragile runtime joins across `D1_MSRMT`, IMD lineage, measuring component, install event, and service point context.

## Grain
One row per processed measurement in `CISADM.D1_MSRMT`.

Natural key:
- `MEASR_COMP_ID`
- `MSRMT_DTTM`

## Domain XML
- Workspace copy: `D1_MSRMT_RPT_CURR_End_User_Friendly.xml`
- Import bundle: `domains/exports/manual_imports/D1_MSRMT_RPT_CURR_End_User_Friendly.xml`
- Keep both copies synchronized when the Domain changes.

## Master Guide
- Full technical guide: `06_master_technical_guide.md`
- Use it for final design, time-valid install-event logic, QA evidence, and deployment/debugging guidance.

## Implemented snapshot
- `00a_legacy_domain_preflight_validation.sql`
- `00_create_snapshot_table.sql`
- `01_refresh_snapshot_procedure.sql`
- `01a_full_history_refresh_procedure.sql`
- `02_schedule_snapshot_job.sql`
- `03_validation_queries.sql`
- `04_intensive_qa_queries.sql`
- `05_qa_results_template.md`
- `06_master_technical_guide.md`
- `07_refresh_strategy_diagnostics.sql`
- `08_fast_before_after_validation.sql`
- `09_rolling_refresh_candidate_procedure.sql`
- `D1_MSRMT_RPT_CURR_End_User_Friendly.xml`

## Current refresh strategy
- One-time baseline option: `01a_full_history_refresh_procedure.sql`
- Ongoing refresh option: `01_refresh_snapshot_procedure.sql`

The active procedure was updated on `2026-04-22` to a rolling `12-month` refresh. It now:
- preserves historical rows older than `12` months
- deletes only the in-window snapshot rows
- reloads only measurements with `MSRMT_DTTM >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12)`

## Validation status
- Fast before/after validation: `08_fast_before_after_validation.sql`
- Manual validation refresh on `2026-04-22` completed in `4.09` minutes
- Prior latest scheduler runtime before cutover was `11.75` minutes
- Before/after validation held:
  - total rows unchanged at `1,680,216`
  - rolling `12-month` monthly parity stayed exact
  - total `MSRMT_VAL` stayed exact
  - total `READING_VAL` stayed exact
  - no duplicate natural-key rows were introduced
