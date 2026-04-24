# FT GL 6-Month Cutover Validation

Date: `2026-04-24`

## Purpose

This document records the evaluation and cutover of
`CISADM.FT_GL_DISTRIBUTION_RPT_CURR` from a rolling `12-month` maintenance
window to a rolling `6-month` maintenance window.

## Why This Was Evaluated

`FT_GL_DISTRIBUTION_RPT_CURR` was still the slowest active scheduled refresh in
the 7-snapshot family at `11.63` minutes on the latest scheduler sample.

The goal was to determine whether reducing the rolling maintenance window from
`12` months to `6` months would materially reduce runtime without losing active
back-posted FT / FT-GL activity.

## Read-Only Safety Checks

### 1. 6-month source footprint

Current source share inside the last `6` months:

- rows in window: `598,238`
- rows older than window: `4,356,368`
- percent of current source rows in window: `12.07%`
- `STATISTIC_AMOUNT` in window: `55,072,740.99897`

### 2. Recent creation landing in older accounting periods

Read-only checks on `CI_FT` returned:

- created last `30` days, accounting date older than `6` months: `0`
- created last `90` days, accounting date older than `6` months: `0`
- created last `180` days, accounting date older than `6` months: `0`

Interpretation:

- current FT creation is not back-posting into periods older than `6` months in
  this environment
- preserving older baseline history in place while rebuilding only the last `6`
  months is operationally safe based on current evidence

## Change Applied

Active procedure updated:

- [02_refresh_snapshot_procedure.sql](/Users/chase/OriginBA-3/sql/performance/snapshots/finance/ft_gl_distribution/02_refresh_snapshot_procedure.sql)

Change:

- `v_window_start` moved from
  `ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12)` to
  `ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -6)`

Preserved baseline remains:

- [02a_full_history_refresh_procedure.sql](/Users/chase/OriginBA-3/sql/performance/snapshots/finance/ft_gl_distribution/02a_full_history_refresh_procedure.sql)

## Manual Refresh Result

Manual procedure execution completed successfully.

Observed elapsed time:

- `353.22` seconds
- `5.89` minutes

Comparison to prior latest scheduler sample:

- prior latest scheduler runtime: `11.63` minutes
- improvement: approximately `5.74` minutes faster

## AFTER QA

### Whole-table parity

- snapshot rows: `4,954,606`
- source rows: `4,954,606`
- snapshot `GL_AMOUNT`: `0`
- source `GL_AMOUNT`: `0`
- snapshot `STATISTIC_AMOUNT`: `475,046,395.33187`
- source `STATISTIC_AMOUNT`: `475,046,395.33187`

### Duplicate natural-key check

- duplicate `(FT_ID, GL_SEQ_NBR)` rows: none

### 6-month active-window expectation

The changed procedure now rebuilds only the last `6` months.

### 12-month sanity check after cutover

Even after narrowing the maintenance window, the preserved `6-to-12-month`
history still matched source exactly for every month returned in the validation
query.

That means:

- current in-window rebuild is correct
- preserved older history remains intact
- no parity drift was introduced by moving from `12` months to `6` months

## Decision

The `6-month` FT/GL rolling window is approved in this environment.

Why:

- source evidence showed no recent back-posting older than `6` months
- runtime dropped from `11.63` minutes to `5.89` minutes on manual validation
- whole-table and monthly parity remained exact after cutover

## Next Operational Step

Let the next scheduled job run on the normal cadence and then refresh the
runtime capture docs so the latest observed scheduler runtime reflects the new
window.
