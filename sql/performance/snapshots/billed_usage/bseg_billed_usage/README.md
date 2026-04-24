# BSEG Billed Usage Snapshot

## Purpose
This folder is for the billing-workstream snapshot derived from the legacy bill / bill segment / billed-usage Jasper domain.

The legacy domain mixes:
- `CI_BILL` as bill header
- `CI_BSEG` as bill-segment fact
- `CI_BSEG_SQ` as billed usage quantity detail
- `CI_BSEG_READ` as read detail
- `CI_BSEG_CALC` as calculation-header detail

## Grain problem
This domain does not have a single grain today.

It mixes:
- one row per bill
- one row per bill segment
- one row per billed service-quantity line
- one row per bill-segment read
- one row per bill-segment calc header

That means the legacy XML will multiply billed amounts and quantities unless the child tables are aggregated first.

## Likely snapshot options
### Option 1
BSEG header snapshot with aggregated usage

Recommended grain:
- one row per `CI_BSEG.BSEG_ID`

Use for:
- billed segment counts
- segment billed amount
- one trusted rolled-up billed usage measure per segment

### Option 2
BSEG SQ snapshot

Recommended grain:
- one row per `CI_BSEG_SQ` line
- natural key: `BSEG_ID`, `UOM_CD`, `TOU_CD`, `SQI_CD`

Use for:
- billed usage by UOM / TOU / SQI
- determinant analysis

Tradeoff:
- segment-level billed amounts will repeat on each SQ line unless allocated separately

## Current recommendation
If the business question is "how much usage was really billed on each bill segment," start by validating at `BSEG` grain and aggregate `CI_BSEG_SQ` up to the segment before mixing in other detail tables.

If users later need analysis by `UOM_CD` / `TOU_CD` / `SQI_CD`, build a separate `BSEG_SQ`-grain snapshot rather than joining `CI_BSEG_READ`, `CI_BSEG_SQ`, and `CI_BSEG_CALC` directly.

Service type can be included safely at this grain from `CI_BSEG.SA_ID -> CI_SA.SA_TYPE_CD`, with description from `CI_SA_TYPE_L`.

Customer name can also be included safely at this grain if it is resolved to one primary account-holder row per `ACCT_ID`.

The raw `CI_SA_TYPE.SVC_TYPE_CD` can be exposed safely as a source field, but it should not be translated into a business-friendly utility description in the base snapshot unless that mapping is validated for the specific client.

## Known legacy domain defects to validate
1. `CI_BSEG_READ`, `CI_BSEG_SQ`, and `CI_BSEG_CALC` are all joined directly to `CI_BSEG` with `inner` joins, which almost certainly multiplies rows.
2. The domain filters `CI_BILL.BILL_STAT_FLG == 'C '`, which must be validated against actual coded values.
3. The domain exposes both billed usage quantities and register-read quantities without a governing rule for which one is the reporting truth.
4. The domain uses `inner` joins to person/account child tables that may be unnecessary for billed-usage reporting and may drop valid billed segments.

## Workflow
1. Run `00a_fast_preflight_validation.sql`.
2. Decide whether the reporting truth should be:
   - `BSEG` grain with aggregated billed usage, or
   - `BSEG_SQ` grain for determinant detail.
3. Build the snapshot from validated SQL logic, not directly from the legacy XML.

## Domain XML
- Workspace copy: `BSEG_BILLED_USAGE_RPT_CURR_End_User_Friendly.xml`
- Import bundle: `domains/exports/manual_imports/BSEG_BILLED_USAGE_RPT_CURR_End_User_Friendly.xml`
- Keep both copies synchronized when the Domain changes.

## Master Guide
- Full technical guide: `07_master_technical_guide.md`
- Use it for end-to-end implementation detail, field inventory, QA results, replication steps, and debugging guidance.

## Implemented snapshot
- `01_create_snapshot_table.sql`
- `02_refresh_snapshot_procedure.sql`
- `02a_full_history_refresh_procedure.sql`
- `03_schedule_snapshot_job.sql`
- `04_validation_queries.sql`
- `05_intensive_qa_queries.sql`
- `06_qa_results_template.md`
- `07_master_technical_guide.md`
- `08_refresh_strategy_diagnostics.sql`
- `09_fast_before_after_validation.sql`
- `10_rolling_refresh_candidate_procedure.sql`
- `BSEG_BILLED_USAGE_RPT_CURR_End_User_Friendly.xml`

## Rolling-window candidate status
- The active procedure was updated on `2026-04-24` to rolling `12-month` maintenance keyed on `BILL_DT`.
- `02a_full_history_refresh_procedure.sql` preserves the original full-history `TRUNCATE + INSERT` version explicitly for first-time deployment into a new database.
- `10_rolling_refresh_candidate_procedure.sql` remains as the original promotion scaffold used for the cutover evidence.
- Validate with:
  - `08_refresh_strategy_diagnostics.sql`
  - `09_fast_before_after_validation.sql`

Rolling maintenance behavior:
- delete only rows where `BILL_DT >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12)`
- reload only that same `12-month` billing slice
- keep older history in place

## Current validation status
- Read-only validation was re-run on `2026-04-24`.
- Recent bill creation did not land into bill periods older than `12` months in the reviewed `30`, `90`, and `180` day slices.
- Rolling `12-month` monthly parity was exact against current raw-source counts and additive totals.
- Whole-table parity was exact for:
  - row count
  - `TOTAL_BILL_SQ`
  - `TOTAL_CALC_AMT`
- Duplicate `BSEG_ID` rows were not present.
- Controlled cutover was executed on `2026-04-24`.
- AFTER QA confirmed:
  - preserved-history rows older than the rolling window remained intact
  - rolling `12-month` monthly parity remained exact
  - whole-table totals remained exact
  - duplicate keys remained absent
- Current status:
  - this snapshot now runs on the validated rolling-window procedure
  - it was promoted before the determinant-grain BSEG snapshot as planned

Reference:
- `sql/performance/snapshots/docs/bseg_rolling_window_validation_2026-04-24.md`
