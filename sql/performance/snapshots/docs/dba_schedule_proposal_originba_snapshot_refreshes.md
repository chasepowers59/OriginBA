# DBA Schedule Proposal for OriginBA Snapshot Refreshes

Scheduling Recommendation Based on Current Refresh Runtime, Current Scheduler Configuration, and Current Refresh Design

## Executive Summary
This document provides scheduling guidance for four OriginBA snapshot refresh tables only:

- `D1_USAGE_SCALAR_DTL_RPT_CURR`
- `BSEG_BILLED_USAGE_RPT_CURR`
- `FT_RPT_CURR`
- `FT_GL_DISTRIBUTION_RPT_CURR`

The current deployed operating model is a once-daily serialized schedule in `GMT`:

1. `FT_RPT_CURR` at `01:00`
2. `BSEG_BILLED_USAGE_RPT_CURR` at `01:30`
3. `FT_GL_DISTRIBUTION_RPT_CURR` at `03:00`
4. `D1_USAGE_SCALAR_DTL_RPT_CURR` at `04:00`

This is the recommended schedule to keep. It reflects the current active job definitions, avoids overlap among the four reviewed objects, and gives the two heavier refreshes, `FT_GL_DISTRIBUTION_RPT_CURR` and `D1_USAGE_SCALAR_DTL_RPT_CURR`, clear isolated windows.

The recommendation has changed from the earlier draft for three reasons:

- all four reviewed objects are now actively scheduled once daily rather than split between a daily usage job and a 6-hour finance cycle
- `D1_USAGE_SCALAR_DTL_RPT_CURR` no longer uses the older full-history monthly-loop refresh shape in the governed package; it now uses a rolling 12-month nightly refresh after a one-time full-history baseline load
- current observed runtimes support the actual deployed order and spacing better than the earlier planning estimates

## Scope
This proposal covers only the four snapshot tables named below. No other snapshot tables are included in this scheduling recommendation.

- `D1_USAGE_SCALAR_DTL_RPT_CURR`
- `BSEG_BILLED_USAGE_RPT_CURR`
- `FT_RPT_CURR`
- `FT_GL_DISTRIBUTION_RPT_CURR`

## Basis for the Recommendation
This recommendation uses the current governed package design and the current scheduler/runtime observations for these four tables.

Inputs used:

- grain
- refresh pattern
- current deployed scheduler interval
- current row count
- latest observed runtime
- current operational sequencing
- current cutover validation for the rolling usage-scalar design

## Reviewed Snapshot Summary

| Snapshot Object | Grain | Current Refresh Pattern | Current Scheduled Time GMT | Current Row Count |
|---|---|---|---|---:|
| `FT_RPT_CURR` | one row per `FT_ID` | `TRUNCATE + INSERT + COMMIT` | `01:00` daily | 4,856,123 |
| `BSEG_BILLED_USAGE_RPT_CURR` | one row per `BSEG_ID` | `TRUNCATE + INSERT + COMMIT` with pre-aggregated child context | `01:30` daily | 2,214,878 |
| `FT_GL_DISTRIBUTION_RPT_CURR` | one row per `FT_ID`, `GL_SEQ_NBR` | `TRUNCATE + INSERT + COMMIT` | `03:00` daily | 4,954,576 |
| `D1_USAGE_SCALAR_DTL_RPT_CURR` | one row per `D1_USAGE_ID`, `SEQ_NUM` | rolling 12-month `DELETE by D1_USAGE_ID + 3-month batched INSERT + COMMIT` after one-time full-history baseline load | `04:00` daily | 720,071 |

## Current Scheduler Configuration

These are the current intended scheduler times in `GMT` for the four reviewed objects.

| Snapshot Object | Job Name | Enabled | State | Repeat Interval | Next Scheduled Pattern |
|---|---|---|---|---|---|
| `FT_RPT_CURR` | `JOB_REFRESH_FT_RPT_CURR` | `TRUE` | `SCHEDULED` | `FREQ=DAILY;BYHOUR=1;BYMINUTE=0;BYSECOND=0` | daily at `01:00 GMT` |
| `BSEG_BILLED_USAGE_RPT_CURR` | `JOB_REFRESH_BSEG_BILLED_USAGE_RPT_CURR` | `TRUE` | `SCHEDULED` | `FREQ=DAILY;BYHOUR=1;BYMINUTE=30;BYSECOND=0` | daily at `01:30 GMT` |
| `FT_GL_DISTRIBUTION_RPT_CURR` | `JOB_REFRESH_FT_GL_DISTRIBUTION_RPT_CURR` | `TRUE` | `SCHEDULED` | `FREQ=DAILY;BYHOUR=3;BYMINUTE=0;BYSECOND=0` | daily at `03:00 GMT` |
| `D1_USAGE_SCALAR_DTL_RPT_CURR` | `JOB_REFRESH_D1_USAGE_SCALAR_DTL_RPT_CURR` | `TRUE` | `SCHEDULED` | `FREQ=DAILY;BYHOUR=4;BYMINUTE=0;BYSECOND=0` | daily at `04:00 GMT` |

## Latest Observed Runtime Findings

Latest observed runtimes from the current active scheduler history are the most important scheduling input because they show how long each job is actually holding the refresh window.

| Snapshot Object | Latest Observed Runtime | Runtime Seconds | Notes |
|---|---|---:|---|
| `BSEG_BILLED_USAGE_RPT_CURR` | `00:03:58` | 238 | shortest of the four current reviewed jobs |
| `FT_RPT_CURR` | `00:05:20` | 320 | short full rebuild |
| `FT_GL_DISTRIBUTION_RPT_CURR` | `00:22:56` | 1,376 | materially heavier than FT header |
| `D1_USAGE_SCALAR_DTL_RPT_CURR` | `00:43:53` | 2,633 | longest reviewed runtime, but now on a controlled daily rolling-window refresh |

## Current Sequencing Gaps

The current deployed schedule creates these explicit gaps:

| From | To | Gap |
|---|---|---|
| `FT_RPT_CURR` `01:00` | `BSEG_BILLED_USAGE_RPT_CURR` `01:30` | `30 minutes` |
| `BSEG_BILLED_USAGE_RPT_CURR` `01:30` | `FT_GL_DISTRIBUTION_RPT_CURR` `03:00` | `90 minutes` |
| `FT_GL_DISTRIBUTION_RPT_CURR` `03:00` | `D1_USAGE_SCALAR_DTL_RPT_CURR` `04:00` | `60 minutes` |

Compared to latest observed runtimes, those buffers are currently large enough to keep the reviewed jobs separated:

- `FT_RPT_CURR` finishes well inside its `30` minute gap
- `BSEG_BILLED_USAGE_RPT_CURR` finishes well inside its `90` minute gap
- `FT_GL_DISTRIBUTION_RPT_CURR` finishes well inside its `60` minute gap
- `D1_USAGE_SCALAR_DTL_RPT_CURR` remains isolated at the end of the sequence, which is appropriate because it is the longest runtime in this four-table set

## Updated Capacity Assessment

The earlier draft used planning estimates and assumed `BSEG_BILLED_USAGE_RPT_CURR` would likely be the heaviest of the finance-family objects. The current measured runtime evidence does not support that assumption.

For the four reviewed objects, the current practical runtime ranking is:

1. `D1_USAGE_SCALAR_DTL_RPT_CURR` at about `43.9` minutes
2. `FT_GL_DISTRIBUTION_RPT_CURR` at about `22.9` minutes
3. `FT_RPT_CURR` at about `5.3` minutes
4. `BSEG_BILLED_USAGE_RPT_CURR` at about `4.0` minutes

Important interpretation:

- `FT_GL_DISTRIBUTION_RPT_CURR` is the heaviest current finance refresh in this four-table group
- `D1_USAGE_SCALAR_DTL_RPT_CURR` is still the heaviest overall reviewed refresh, but its current governed design is materially better controlled than the older full-history model
- `BSEG_BILLED_USAGE_RPT_CURR` is currently active and should no longer be described as intentionally stale or excluded from the operating cycle

## Design Updates That Affect Scheduling

### `D1_USAGE_SCALAR_DTL_RPT_CURR`
The current governed package design is no longer the older full-history monthly-loop concept.

Current operational model:

- one-time full-history baseline load first
- then switch to the rolling nightly procedure
- nightly procedure rebuilds only the rolling last 12 months
- nightly rebuild runs in 3-month batches
- before/after validation confirmed preserved row counts and additive quantity totals during cutover

Why this matters for schedule planning:

- the object is still the longest runtime in this document
- but it is now a controlled rolling-window refresh, not an unbounded full-history nightly rebuild
- it should still stay isolated at the end of the nightly sequence

### `BSEG_BILLED_USAGE_RPT_CURR`
The current document should treat this as active and scheduled daily at `01:30 GMT`, not as a paused or stale billing object.

### `FT_RPT_CURR` and `FT_GL_DISTRIBUTION_RPT_CURR`
These are now once-daily scheduled finance jobs in this proposal, not members of an active 6-hour refresh family.

## Scheduling Recommendation
Keep the current deployed once-daily serialized schedule exactly as follows:

1. `FT_RPT_CURR` at `01:00 GMT`
2. `BSEG_BILLED_USAGE_RPT_CURR` at `01:30 GMT`
3. `FT_GL_DISTRIBUTION_RPT_CURR` at `03:00 GMT`
4. `D1_USAGE_SCALAR_DTL_RPT_CURR` at `04:00 GMT`

This is the recommended execution order for the reviewed four-table set.

## Why This Order

### `FT_RPT_CURR` first at `01:00 GMT`
`FT_RPT_CURR` is a short and structurally simple full rebuild. Starting it first clears the smallest finance job early and leaves a clean buffer before the next object.

### `BSEG_BILLED_USAGE_RPT_CURR` second at `01:30 GMT`
`BSEG_BILLED_USAGE_RPT_CURR` is also short in current observed runtime and fits safely after FT header. The current `30` minute gap is materially larger than its latest observed runtime.

### `FT_GL_DISTRIBUTION_RPT_CURR` third at `03:00 GMT`
`FT_GL_DISTRIBUTION_RPT_CURR` is the heaviest finance refresh in this four-table group and should remain later in the sequence with a wide buffer ahead of it. The current `90` minute gap after BSEG is conservative and operationally safe.

### `D1_USAGE_SCALAR_DTL_RPT_CURR` last at `04:00 GMT`
`D1_USAGE_SCALAR_DTL_RPT_CURR` is the longest reviewed refresh and should remain isolated. The current `60` minute buffer after FT GL is still larger than FT GL's latest observed runtime and gives the scalar refresh a clean starting point.

## Current Operational Position
This proposal is now aligned to the current implemented schedule rather than an earlier future-state estimate.

Operationally:

- all four reviewed objects are active in the schedule
- all four reviewed objects are once-daily jobs in `GMT`
- the schedule is already serialized
- the current buffers are larger than the latest observed runtimes
- the current layout should be retained unless future measured runtimes change materially

## Implementation Guidance

- Keep the four reviewed jobs on the exact current daily times documented above.
- Do not collapse the gaps unless measured runtimes stay stable across a broader observation window.
- Keep `D1_USAGE_SCALAR_DTL_RPT_CURR` at the end of the sequence because it remains the longest reviewed runtime.
- Continue to validate `D1_USAGE_SCALAR_DTL_RPT_CURR` against preserved row counts and additive totals if the rolling-window procedure changes again.
- If `FT_GL_DISTRIBUTION_RPT_CURR` runtime grows materially above the current observed `22.93` minutes, review the `03:00` to `04:00` buffer before changing the sequence.

## Assumptions and Limits

- This document covers only the four reviewed tables.
- Runtime values in this document reflect the current observed scheduler history, not a long-term statistical baseline.
- Exact segment storage is still estimated from Oracle statistics, not exact segment MB.
- The schedule recommendation assumes no other external batch job materially interferes with the `01:00` to `05:00 GMT` window.
- `D1_USAGE_SCALAR_DTL_RPT_CURR` depends on the documented deployment rule that a full-history baseline must exist before the rolling nightly procedure is used.

## Final Recommendation Summary
Based on the current deployed scheduler settings, current refresh design, and current observed runtimes, the recommended schedule for these four reviewed snapshots is the exact schedule already in place:

- `FT_RPT_CURR` at `01:00 GMT`
- `BSEG_BILLED_USAGE_RPT_CURR` at `01:30 GMT`
- `FT_GL_DISTRIBUTION_RPT_CURR` at `03:00 GMT`
- `D1_USAGE_SCALAR_DTL_RPT_CURR` at `04:00 GMT`

This schedule should be retained as the current supported operating model for the reviewed four-table set.
