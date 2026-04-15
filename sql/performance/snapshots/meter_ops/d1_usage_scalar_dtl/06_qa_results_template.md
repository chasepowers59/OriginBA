# D1_USAGE_SCALAR_DTL_RPT_CURR QA Results

## Run Metadata
- Environment: `DEV` (user-run in SQL Developer)
- Run date: `2026-04-13`
- Run by: User in SQL Developer; results documented in repo by Codex
- Snapshot object: `CISADM.D1_USAGE_SCALAR_DTL_RPT_CURR`
- Validation SQL used:
  - `04_validation_queries.sql`
  - `05_intensive_qa_queries.sql`

## Summary
- Pass / Fail: `Pass`
- Ready for ad hoc use: `Yes`
- Key blockers: `None for scalar-detail parity or additive quantity truth`
- Residual risks:
  - `DIVISION_CD`, `BO_STATUS_REASON_CD`, and `US_BO_STATUS_REASON_CD` remain code-only by accepted business decision
  - code-only operational fields should be treated as traceability fields, not required translated end-user dimensions

## Population Boundary Decision
- Included scalar rows: `All D1_USAGE_SCALAR_DTL rows whose parent D1_USAGE row has at least one usable timestamp among START_DTTM, CRE_DTTM, or STATUS_UPD_DTTM`
- Excluded scalar rows: `Only scalar rows whose parent usage would fail the timestamped batch boundary rule`
- Reason: `This snapshot is designed to preserve scalar-detail quantity truth while keeping refreshes practical through monthly batching`

## Source Parity
- Source scalar count: `720,071`
- Snapshot scalar count: `720,071`
- Count difference: `0`
- Source `QUANTITY` total: `8.6068E+10`
- Snapshot `QUANTITY` total: `8.6068E+10`
- Difference: `0`
- Source `FINAL_QUANTITY` total: `8.6068E+10`
- Snapshot `FINAL_QUANTITY` total: `8.6068E+10`
- Difference: `0`

## Anti-Join And Grain Checks
- Duplicate `D1_USAGE_ID, SEQ_NUM` rows: `0 implied by exact row parity plus zero anti-joins on the natural key`
- Source rows missing in snapshot: `0`
- Snapshot rows not in source: `0`

## Raw-Code-Only Business Fields
- `DIVISION_CD` include with description?: `Keep as code-only; business translation not required for release`
- status reason codes include with description?: `Keep BO_STATUS_REASON_CD and US_BO_STATUS_REASON_CD as code-only; translation not required for release`
- Fields excluded from end-user surface: `None required for numeric acceptance`
- Reason for exclusion: `N/A`

## Utility / Business Context Decision Log
- Included scalar quantity fields: `QUANTITY`, `FINAL_QUANTITY`, raw and final UOM / TOU / SQI context, measurement values, usage flags, multipliers, and use percent`
- Included billing/customer fields: `usage header context, subscription context, optional C1 billing bridge, bill segment context, SA/account/customer context, and premise address context`
- Excluded operational detail: `No lower-grain determinant decomposition beyond the scalar-detail sequence itself`
- Schema features not used in this tenant: `translated descriptions for DIVISION_CD, BO_STATUS_REASON_CD, and US_BO_STATUS_REASON_CD are not maintained in the current release shape`
- Action taken on unused features: `accept the three fields as code-only and do not block release on missing description columns`

## Final Decision
- Promote as-is: `Yes`
- Needs lookup additions: `No; accepted code-only fields can remain as-is`
- Needs population change: `No`
- Needs documentation update: `Completed; master technical guide added for this snapshot`
