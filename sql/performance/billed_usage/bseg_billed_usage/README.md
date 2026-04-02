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

## Implemented snapshot
- `01_create_snapshot_table.sql`
- `02_refresh_snapshot_procedure.sql`
- `03_schedule_snapshot_job.sql`
- `04_validation_queries.sql`
