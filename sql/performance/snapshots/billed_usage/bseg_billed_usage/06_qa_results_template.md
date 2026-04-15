# BSEG_BILLED_USAGE_RPT_CURR QA Results

## Run Metadata
- Environment: `DEV` (user-run in SQL Developer)
- Run date: `2026-04-10`
- Run by: User in SQL Developer; results documented in repo by Codex
- Snapshot object: `CISADM.BSEG_BILLED_USAGE_RPT_CURR`
- Validation SQL used:
  - `04_validation_queries.sql`
  - `05_intensive_qa_queries.sql`

## Summary
- Pass / Fail: `Pass`
- Ready for ad hoc use: `Yes`
- Key blockers: `None for source parity or additive billing truth`
- Residual risks:
  - bill-cycle descriptions are missing at high volume where source bill-cycle lookup coverage appears incomplete or source bill-cycle values are null
  - sole determinant/rate descriptions are not fully maintained for all source codes
  - utility type and switch decodes remain governance decisions rather than numeric blockers

## Population Boundary Decision
- Completed bills only confirmed: `Yes`
- Incomplete / pending bills intentionally excluded: `Yes`
- Reason: `This snapshot is for billed truth at completed bill-segment grain, not in-flight billing operations`

## Source Parity
- Source completed `BSEG` count: `2,214,878`
- Snapshot `BSEG` count: `2,214,878`
- Count difference: `0`
- Source `TOTAL_BILL_SQ` equivalent: `3.3090E+10`
- Snapshot `TOTAL_BILL_SQ`: `3.3090E+10`
- Difference: `0`
- Source `TOTAL_CALC_AMT` equivalent: `261,674,711`
- Snapshot `TOTAL_CALC_AMT`: `261,674,711`
- Difference: `0`

## Anti-Join And Grain Checks
- Duplicate `BSEG_ID` rows: `0`
- Source rows missing in snapshot: `0`
- Snapshot rows not in source: `0`
- Sample missing `BSEG_ID` values: `None; sample query returned no rows`
- Sample extra `BSEG_ID` values: `None; sample query returned no rows`
- Notes:
  - aggregated child parity passed exactly
  - rows with SQ: `1,873,559 / 1,873,559`
  - rows with reads: `623,115 / 623,115`
  - rows with calc headers: `2,214,232 / 2,214,232`

## Description And Lookup Coverage
- Bill status mismatches: `0`
- BSEG status mismatches: `0`
- SA type mismatches: `0`
- Customer class mismatches: `Not directly audited in current pack; sample rows looked consistent`
- Collection class mismatches: `Not directly audited in current pack; sample rows looked consistent`
- Account management group mismatches: `Not directly audited in current pack`
- Budget plan mismatches: `Not directly audited in current pack`
- Cancel reason mismatches: `Not directly audited in current pack`
- Source lookup gaps found:
  - `BILL_BILL_CYC_DESC` missing rows in validation output: `1,193,988`
  - `BSEG_BILL_CYC_DESC` missing rows in validation output: `1,214,889`
  - single-determinant rows missing `SOLE_UOM_DESC` when code present: `129,171`
  - single-determinant rows missing `SOLE_TOU_DESC` when code present: `985,799`
  - single-determinant rows missing `SOLE_SQI_DESC` when code present: `856,628`
  - single-rate rows missing `SOLE_RS_DESC` when code present: `31,306`

## Raw-Code-Only Business Fields
- `UTILITY_TYPE_CD` include with description?: `Keep the code in the snapshot; do not invent a description until a client-approved utility mapping exists`
- switch fields include with description?: `Keep switch codes in the snapshot for traceability; do not treat switch decodes as a parity blocker`
- Sole determinant description coverage when required: `Incomplete due to source lookup coverage gaps for UOM / TOU / SQI`
- Sole rate description coverage when required: `Mostly present, with 31,306 source rows lacking resolved sole rate description`
- Fields excluded from end-user surface: `None required for numeric acceptance`
- Reason for exclusion: `N/A`

## Utility / Business Context Decision Log
- Trusted additive measure: `TOTAL_BILL_SQ` for billed quantity, with `TOTAL_CALC_AMT` carried as billed amount support`
- Included billing context:
  - completed bill status
  - bill segment status
  - account and customer context
  - service type
  - customer and collection class
  - bill cycles
  - budget plan
  - aggregated SQ, read, and calc context
- Excluded billing context:
  - incomplete or pending bills
  - determinant-line grain detail beyond aggregated segment-level facts
- Schema features not used in this tenant:
  - readable utility-type description mapping is not yet client-governed
  - TOU / SQI / some rate descriptions are not consistently maintained for all source values
  - bill-cycle descriptions are not consistently available for all source bill-cycle values
- Action taken on unused features:
  - keep source codes where useful
  - document lookup gaps instead of inventing translations
  - treat these as semantic cleanup items, not population blockers

## Final Decision
- Promote as-is: `Yes`
- Needs lookup additions: `Optional source-data remediation only; not a snapshot blocker`
- Needs population change: `No`
- Needs documentation update: `Completed for QA results; keep lookup-gap notes in ongoing release documentation`
