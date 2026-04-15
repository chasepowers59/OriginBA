# FT_RPT_CURR QA Results

## Run Metadata
- Environment: `DEV` (user-run in SQL Developer)
- Run date: `2026-04-09`
- Run by: User in SQL Developer; results documented in repo by Codex
- Snapshot object: `CISADM.FT_RPT_CURR`
- Refresh procedure version checked: `02_refresh_snapshot_procedure.sql` after description-column enhancement
- Validation SQL used:
  - `04_validation_queries.sql`
  - `06_intensive_qa_queries.sql`

## Summary
- Pass / Fail: `Pass`
- Ready for ad hoc use: `Yes`
- Key blockers: `None for source parity or numeric integrity`
- Residual risks:
  - source lookup gaps remain for `SA_TYPE_CD`, `ADJ_TYPE_CD`, `BILL_CYC_CD`, and `ACCT_MGMT_GRP_CD`
  - `ACCT_MGMT_GRP_CD` is populated in source but has no maintained translation row in this tenant
  - `3` rows show `FREEZE_DTTM < CRE_DTTM`; treat as source-data anomalies unless business requires correction

## Source Parity
- Source FT count: `4,856,123`
- Snapshot FT count: `4,856,123`
- Count difference: `0`
- Source `CUR_AMT` total: `3,009,107.78`
- Snapshot `CUR_AMT` total: `3,009,107.78`
- `CUR_AMT` difference: `0`
- Source `TOT_AMT` total: `3,682,478.38`
- Snapshot `TOT_AMT` total: `3,682,478.38`
- `TOT_AMT` difference: `0`

## Natural Key And Anti-Join Checks
- Duplicate `FT_ID` rows: `0`
- Source rows missing in snapshot: `0`
- Snapshot rows not in source: `0`
- Notes:
  - FT-type-level row counts and amounts matched exactly for `AD`, `AX`, `BS`, `BX`, `PS`, and `PX`
  - anti-join checks were clean in both directions

## Optional Child Coverage
- SA/account context parity result: `Pass`
- Bill segment overlay parity result: `Pass`
- Adjustment overlay parity result: `Pass`
- Payment overlay parity result: `Pass`
- Notes:
  - child overlays populate only for the intended FT families
  - key child identifiers matched exactly: `ACCT_ID`, `BSEG_ID`, `ADJ_ID`, `PAY_SEG_ID`

## Description And Lookup Coverage
- FT type description mismatches: `0`
- GL distribution status description mismatches: `0`
- SA status description mismatches: `0`
- SA type description mismatches: `0`
- Bill segment status description mismatches: `0`
- Adjustment status description mismatches: `0`
- Adjustment type description mismatches: `0`
- Freeze user name mismatches: `0`
- Source lookup gaps found:
  - `SA_TYPE_CD`: `26`
  - `BILL_CYC_CD`: `675`
  - `ACCT_MGMT_GRP_CD`: all populated rows in snapshot because the single tenant code has no lookup row
  - `ADJ_TYPE_CD`: `35`
- Notes:
  - mismatch counts are `0`, so the snapshot is faithfully reflecting source and lookup-table behavior
  - remaining issues are source lookup coverage issues, not snapshot logic defects

## Business Description Coverage
- `CUST_CL_DESC` populated and matched: `Yes`
- `COLL_CL_DESC` populated and matched: `Yes`
- `BILL_CYC_DESC` populated and matched: `Yes, where source lookup exists`
- `ACCT_MGMT_GRP_DESC` populated and matched: `No; source lookup row is not maintained in this tenant`
- Remaining source lookup exceptions:
  - `1` distinct `BILL_CYC_CD` is missing lookup translation and repeats across `675` rows
  - `1` distinct `ACCT_MGMT_GRP_CD` is present and has no lookup translation
- Fields still excluded from end-user surface:
  - none required for numeric verification
  - if business wants only translated dimensions, consider hiding `ACCT_MGMT_GRP_*` from the end-user Domain until source lookup maintenance exists

## Utility / Business Context Decision Log
- Population boundary decision: `Include all non-redundant FT rows where CI_FT.REDUNDANT_SW = 'N'`
- Included FT families: `AD`, `AX`, `BS`, `BX`, `PS`, `PX`
- Excluded FT families: `No additional FT-type exclusion beyond source non-redundant filter`
- Included account / SA context:
  - `ACCT_ID`
  - SA status and service agreement type
  - customer class
  - collection class
  - bill cycle
  - optional bill segment, adjustment, and pay segment overlays
- Excluded context:
  - GL-line detail
  - chart-of-accounts attributes
- Schema features not used in this tenant:
  - maintained account-management-group translation lookup appears unused or unmaintained
- Action taken on unused features:
  - keep `ACCT_MGMT_GRP_CD` and `ACCT_MGMT_GRP_DESC` in snapshot for traceability
  - document translation gap instead of inventing a custom decode

## Sample Evidence
- Attach or paste key query outputs:
  - source/snapshot FT count parity: `4,856,123 / 4,856,123`
  - source/snapshot amount parity: `CUR_AMT 3,009,107.78 / 3,009,107.78`, `TOT_AMT 3,682,478.38 / 3,682,478.38`
  - FT-type-level parity passed across all six FT families
- Attach anti-join samples if non-zero: `None; both anti-join checks returned 0`
- Attach raw-code sample rows if any:
  - sample rows confirmed new description fields populate correctly for customer class, collection class, and bill cycle
  - sample rows confirmed `ACCT_MGMT_GRP_DESC` remains null because source lookup is missing

## Final Decision
- Promote as-is: `Yes`
- Needs column additions: `No`
- Needs lookup additions: `Optional source-data remediation only; not a snapshot blocker`
- Needs population change: `No`
- Needs documentation update: `Completed; document source lookup exceptions in ongoing release notes`
