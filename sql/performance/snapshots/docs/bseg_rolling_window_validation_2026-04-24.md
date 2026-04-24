# BSEG Rolling Window Validation

As of `2026-04-24`

## Purpose

This note records the read-only evidence gathered before any procedure change
 to the active BSEG snapshot refreshes:

- `CISADM.BSEG_BILLED_USAGE_RPT_CURR`
- `CISADM.BSEG_SQ_USAGE_RPT_CURR`

The goal was to confirm whether the same rolling `12-month` maintenance model
 already adopted for finance and meter snapshots can be applied safely to the
 billing snapshots without changing grain or reporting totals.

## Approach

The evaluation intentionally stayed read-only.

The following scripts were executed against the connected Oracle environment:

1. `billed_usage/bseg_billed_usage/08_refresh_strategy_diagnostics.sql`
2. `billed_usage/bseg_sq_usage/09_refresh_strategy_diagnostics.sql`
3. `billed_usage/bseg_billed_usage/09_fast_before_after_validation.sql`
4. `billed_usage/bseg_sq_usage/10_fast_before_after_validation.sql`

This sequence was chosen for a specific reason:

- diagnostics first:
  confirm whether recently created billing rows are back-posting into periods
  older than the proposed rolling maintenance window
- parity validation second:
  confirm that the current snapshot contents already match raw-source monthly
  counts and additive totals inside the last `12` months

## Findings

### `BSEG_BILLED_USAGE_RPT_CURR`

- snapshot rows: `2,214,878`
- rows in last `12` months: `352,743`
- rows in last `24` months: `832,699`
- recent bill creation into periods older than `12` months:
  - created last `30` days: `0`
  - created last `90` days: `0`
  - created last `180` days: `0`
- lag profile is overwhelmingly `0_TO_7_DAYS`
- rolling `12-month` monthly parity: exact
- whole-table totals:
  - row count: exact
  - `TOTAL_BILL_SQ`: exact
  - `TOTAL_CALC_AMT`: exact
- duplicate `BSEG_ID` rows: none

### `BSEG_SQ_USAGE_RPT_CURR`

- snapshot rows: `3,745,478`
- rows in last `12` months: `996,542`
- rows in last `24` months: `2,353,496`
- recent bill creation into periods older than `12` months:
  - created last `30` days: `0`
  - created last `90` days: `0`
  - created last `180` days: `0`
- lag profile is overwhelmingly `0_TO_7_DAYS`
- rolling `12-month` monthly parity: exact
- whole-table totals:
  - row count: exact
  - `TOTAL_BILL_SQ`: exact
  - `TOTAL_INIT_SQ`: exact
- duplicate determinant natural keys: none

## Interpretation

The evidence currently supports a rolling `12-month` maintenance strategy for
 both BSEG snapshots.

Why this conclusion is reasonable:

- recent bill creation is not landing into billing periods older than `12`
  months in the reviewed `30`, `90`, and `180` day slices
- the current snapshot contents already tie exactly to raw-source monthly
  counts and additive totals for the proposed maintenance window
- the older history can remain in place as a preserved baseline, matching the
  operating model already adopted for the approved finance and meter snapshots

## Refresh Model Clarification

The active rolling maintenance model does **not** truncate the full snapshot
 table.

It does this instead:

- calculate `v_window_start = ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12)`
- delete only snapshot rows where `BILL_DT >= v_window_start`
- insert refreshed source rows for that same `BILL_DT >= v_window_start` slice
- leave all rows older than the rolling window in place as preserved baseline
  history

That preserved older history is why the original full-history procedures must
 remain in the repo for first-time deployment into a new environment.

## Recommended Cutover Order

Do not cut both BSEG procedures at once.

Recommended order:

1. `BSEG_BILLED_USAGE_RPT_CURR`
2. `BSEG_SQ_USAGE_RPT_CURR`

This order is preferred because the segment-level billed-usage snapshot is the
 simpler artifact and provides the cleaner first proof that the billing-window
 maintenance model behaves correctly under live refresh.

## Required QA For Any Cutover

Before changing either procedure:

1. save validator output as `BEFORE`
2. deploy the candidate procedure for one snapshot only
3. run one manual refresh
4. save validator output as `AFTER`
5. compare the two outputs

The cutover is acceptable only if all of the following hold:

- whole-table row count remains unchanged
- rolling `12-month` monthly parity remains exact
- whole-table additive totals remain exact
- duplicate natural-key checks return zero rows
- older-than-window history is still present in the snapshot

## Important Constraints

- no change to snapshot grain
- no change to additive measure definitions
- no change to report-facing business logic beyond refresh maintenance scope
- preserve historical baseline rows older than the rolling window
- preserve the original full-history procedures for first-time deployment into
  any new database

## Cutover Execution

After the read-only validation passed, both billing snapshots were promoted in
 controlled sequence on `2026-04-24`.

Execution order:

1. deploy rolling procedure for `BSEG_BILLED_USAGE_RPT_CURR`
2. run one manual refresh
3. run AFTER validation
4. deploy rolling procedure for `BSEG_SQ_USAGE_RPT_CURR`
5. run one manual refresh
6. run AFTER validation

Why this order was used:

- the segment-level billed-usage snapshot is the simpler artifact
- validating it first reduced the risk of changing both billing refreshes at
  once
- the determinant-grain snapshot depends on the same billing-period behavior,
  but has a larger in-window row volume

## AFTER QA Outcome

### `BSEG_BILLED_USAGE_RPT_CURR`

- preserved-history rows older than the rolling window remained `1,862,135`
- rolling `12-month` monthly parity remained exact
- whole-table parity remained exact for:
  - row count
  - `TOTAL_BILL_SQ`
  - `TOTAL_CALC_AMT`
- duplicate `BSEG_ID` rows remained absent
- refreshed in-window rows show new `LOAD_DTTM` at `2026-04-24 12:49:18.266717`

### `BSEG_SQ_USAGE_RPT_CURR`

- preserved-history rows older than the rolling window remained `2,748,936`
- rolling `12-month` monthly parity remained exact
- whole-table parity remained exact for:
  - row count
  - `TOTAL_BILL_SQ`
  - `TOTAL_INIT_SQ`
- duplicate determinant natural keys remained absent
- refreshed in-window rows show new `LOAD_DTTM` at `2026-04-24 12:53:33.243211`

## Decision Status

- `BSEG_BILLED_USAGE_RPT_CURR`: rolled to active `12-month` maintenance and validated
- `BSEG_SQ_USAGE_RPT_CURR`: rolled to active `12-month` maintenance and validated
- active repo procedure files were updated to match the deployed database state
- `02a_full_history_refresh_procedure.sql` remains the first-run deployment path
  for both snapshots
