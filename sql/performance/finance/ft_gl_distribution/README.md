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

## Implemented snapshot
- `01_create_snapshot_table.sql`
- `02_refresh_snapshot_procedure.sql`
- `03_schedule_snapshot_job.sql`
- `04_validation_queries.sql`
