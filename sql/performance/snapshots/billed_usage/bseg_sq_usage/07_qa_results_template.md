# BSEG_SQ_USAGE_RPT_CURR QA Results

## Run Metadata
- Environment: `DEV` (user-run in SQL Developer)
- Run date: `2026-04-10`
- Run by: User in SQL Developer; results documented in repo by Codex
- Snapshot object: `CISADM.BSEG_SQ_USAGE_RPT_CURR`
- Validation SQL used:
  - `04_validation_queries.sql`
  - `06_intensive_qa_queries.sql`

## Summary
- Pass / Fail: `Pass`
- Ready for ad hoc use: `Yes, for determinant-grain billed usage analysis`
- Key blockers: `None for determinant grain or additive quantity parity`
- Residual risks:
  - bill-cycle descriptions are missing at high volume where source bill-cycle lookup coverage appears incomplete or source values are null
  - UOM, TOU, and SQI descriptions are not fully maintained in source lookup data
  - utility type and switch decodes remain governance decisions rather than parity blockers

## Population Boundary Decision
- Completed bills only confirmed: `Yes`
- Incomplete / pending bills intentionally excluded: `Yes`
- Reason: `This snapshot is for completed-bill determinant truth, not in-flight billing operations`

## Source Parity
- Source determinant row count: `3,745,478`
- Snapshot determinant row count: `3,745,478`
- Count difference: `0`
- Source `TOTAL_BILL_SQ` equivalent: `3.3090E+10`
- Snapshot `TOTAL_BILL_SQ`: `3.3090E+10`
- Difference: `0`
- Source `TOTAL_INIT_SQ` equivalent: `3.3090E+10`
- Snapshot `TOTAL_INIT_SQ`: `3.3090E+10`
- Difference: `0`

## Anti-Join And Grain Checks
- Duplicate determinant rows: `0`
- Source rows missing in snapshot: `0`
- Snapshot rows not in source: `0`
- Notes:
  - determinant natural key is preserved at `BSEG_ID`, `UOM_CD`, `TOU_CD`, `SQI_CD`
  - `SQ_LINE_COUNT` also matched source in validation output: `3,745,478`
  - determinant-count-by-segment distribution shows many multi-determinant bill segments, confirming this is the correct snapshot for usage-detail analysis rather than `BSEG_BILLED_USAGE_RPT_CURR`

## Raw-Code-Only Business Fields
- `UTILITY_TYPE_CD` include with description?: `Keep the code in the snapshot; do not invent a description until a client-approved utility mapping exists`
- switch fields include with description?: `Keep switch codes in the snapshot for traceability; do not treat switch decodes as a parity blocker`
- Fields excluded from end-user surface: `None required for numeric acceptance`
- Reason for exclusion: `N/A`

## Utility / Business Context Decision Log
- Trusted additive measure: `TOTAL_BILL_SQ`, with `TOTAL_INIT_SQ` as supporting determinant-level quantity context`
- Included determinant context:
  - `BSEG_ID`
  - `UOM_CD`, `TOU_CD`, `SQI_CD`
  - determinant-level billed and initial quantity
  - bill, segment, account, customer, service type, and budget-plan context
  - determinant-count-per-segment support
- Excluded billed-dollar context: `Billed amount is intentionally not the main promise of this snapshot; bill-segment billed amount belongs in BSEG_BILLED_USAGE_RPT_CURR`
- Schema features not used in this tenant:
  - readable utility-type description mapping is not yet client-governed
  - TOU descriptions are entirely absent in current validation output for populated rows
  - many UOM and SQI descriptions are missing from source lookup coverage
  - bill-cycle descriptions are not consistently available for all source bill-cycle values
- Action taken on unused features:
  - keep source codes where useful
  - document lookup gaps instead of inventing translations
  - treat these as semantic cleanup items, not determinant-parity blockers

## Description And Lookup Coverage
- Bill status description missing rows: `0`
- BSEG status description missing rows: `0`
- SA type description missing rows: `0`
- Customer name missing rows: `0`
- Bill bill-cycle descriptions missing where code exists: `874,192`
- BSEG bill-cycle descriptions missing where code exists: `945,555`
- UOM descriptions missing where code exists: `1,943,111`
- TOU descriptions missing where code exists: `3,745,478`
- SQI descriptions missing where code exists: `1,487,857`
- Utility/switch desc columns present: `No; by design/governance decision, not treated as parity failure`

## Final Decision
- Promote as-is: `Yes`
- Needs lookup additions: `Optional source-data remediation only; not a snapshot blocker`
- Needs population change: `No`
- Needs documentation update: `Completed for QA results; keep lookup-gap notes in ongoing release documentation`
