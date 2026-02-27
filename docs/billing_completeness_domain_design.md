# Billing Completeness Domain Design (C2M)

## Business Question
How do we verify that all expected Bills were generated, and identify missed Bills by Bill cycle / Bill date / premise?

## Recommended Output
Create one domain and two report views:
1. **Cycle Completion Summary** (operations dashboard)
2. **Missing Bill Exceptions** (action queue)

## Core Logic
For each `BILL_CYC_CD` and billing window/date:
1. Compute **generated Bills** from `CI_BILL`.
2. Compute **generated Bill Segments** from `CI_BSEG`.
3. Compare and flag reconciliation outcomes:
   - `MISSING_BSEG`: Bill exists but no Bill Segment.
   - `ORPHAN_BSEG`: Bill Segment exists without Bill.
   - `PRESENT`: Bill and Bill Segment both present.

## Source-of-Truth Tables (from Bill Segment domain export)
1. `CISADM.CI_BILL`
   - `BILL_ID`, `BILL_CYC_CD`, `ACCT_ID`, `BILL_DT`, `BILL_STAT_FLG`, `CRE_DTTM`, `COMPLETE_DTTM`
2. `CISADM.CI_BSEG`
   - `BSEG_ID`, `BILL_ID`, `BILL_CYC_CD`, `SA_ID`, `PREM_ID`, `BSEG_STAT_FLG`, `START_DT`, `END_DT`, `CRE_DTTM`
3. `CISADM.CI_ACCT`
   - `ACCT_ID`, `BILL_CYC_CD`
4. `CISADM.CI_BILL_CYC_L`
   - `BILL_CYC_CD`, `LANGUAGE_CD`, `DESCR`
5. `CISADM.CI_LOOKUP_VAL_L`
   - `FIELD_NAME`, `FIELD_VALUE`, `LANGUAGE_CD`, `DESCR`

## Domain Dataset Strategy
Use derived SQL tables as domain base:
- Summary grain: one row per `BILL_CYC_CD + BILL_DATE + BILL_CREATE_DATE`.
- Detail grain: one row per bill/segment reconciliation record.
- Include `SA_ID` and `PREM_ID` from `CI_BSEG` for routing exceptions.

## Required Filters
1. `BILL_CYC_CD`
2. `BILL_DATE` (or `BILL_CREATE_DATE` / `BILL_SEGMENT_CREATE_DATE`)
3. `BILL_STATUS` (optional)
4. `RECONCILIATION_RESULT` (`MISSING_BSEG`, `ORPHAN_BSEG`, `PRESENT`)

## Required KPIs
1. Generated Bills
2. Generated Bill Segments
3. Distinct Premises
4. Bills Without Segment
5. Bill Segment Completion %
6. Missing/Orphan exception counts

## Exception Use Cases
1. Bill header exists but no segment.
2. Segment exists without bill header.
3. Segment exists with non-final status.
4. Multiple cycles on same date with outlier completion.

## Build Recommendation
For performance and clarity:
1. Build SQL as reusable view/table expression first.
2. Point Jasper Domain to that object (and keep raw base tables as optional joins).
3. Add lookup descriptions for status fields (`BILL_STAT_FLG`, `BSEG_STAT_FLG`).

## Validation Checklist
1. Reconcile totals against nightly batch control counts.
2. Spot-check 10 missing exceptions in UI.
3. Validate by cycle and by premise sample.
4. Compare against previous 7 days for anomaly spikes.
