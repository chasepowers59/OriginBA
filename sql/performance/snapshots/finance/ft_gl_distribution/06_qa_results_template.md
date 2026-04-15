# FT_GL_DISTRIBUTION_RPT_CURR QA Results

## Run Metadata
- Environment: `DEV` (user-run in SQL Developer)
- Run date: `2026-04-13`
- Run by: User in SQL Developer; results documented in repo by Codex
- Snapshot object: `CISADM.FT_GL_DISTRIBUTION_RPT_CURR`
- Refresh procedure version checked: `02_refresh_snapshot_procedure.sql`
- Validation SQL used:
  - `04_validation_queries.sql`
  - `05_intensive_qa_queries.sql`

## Summary
- Pass / Fail: `Pass`
- Ready for ad hoc use: `Yes`
- Key blockers: `None for source parity or numeric integrity`
- Residual risks:
  - source lookup gaps remain for some optional business descriptions
  - raw switch/code fields are technical and should only be surfaced in Domain if the business has a real use case
  - `IS_LATEST_BATCH_NBR` is intentionally not populated in the current procedure and should not be used as an automated latest-batch flag

## Source Parity
- Source GL line count: `4,954,576`
- Snapshot GL line count: `4,954,576`
- Count difference: `0`
- Source `GL_AMOUNT` total: `0`
- Snapshot `GL_AMOUNT` total: `0`
- `GL_AMOUNT` difference: `0`
- Source `STATISTIC_AMOUNT` total: `475,046,395`
- Snapshot `STATISTIC_AMOUNT` total: `475,046,395`
- `STATISTIC_AMOUNT` difference: `0`

## Natural Key And Anti-Join Checks
- Duplicate `FT_ID, GL_SEQ_NBR` rows: `0` based on parity outputs and clean anti-join results
- Source rows missing in snapshot: `0`
- Snapshot rows not in source: `0`
- FT-level GL line count mismatches: `Not yet rerun after QA pack correction; current aggregate evidence shows exact row parity`
- Notes:
  - distinct `FT_ID` count matched exactly: `2,322,703`
  - `GL_ACCT + DST_ID` parity section returned no differences
  - FT-type-level row counts and amounts matched exactly across all six FT families

## Overlay And Context Coverage
- Account context parity result: `Pass`
- Person/customer trace parity result: `Pass`
- Bill segment overlay parity result: `Pass`
- Adjustment overlay parity result: `Pass`
- Payment segment overlay parity result: `Pass`
- Balance control group ID parity result: `Pass`
- Balance control group status/description parity result: `No description mismatches`
- Notes:
  - overlay counts aligned for account, person, bill segment, adjustment, payment-segment, and balance-control-group context

## Batch Provenance Coverage
- `BATCH_CD` parity result: `Pass; 0 mismatched rows`
- `BATCH_NBR` parity result: `Pass; 0 mismatched rows`
- `IS_LATEST_BATCH_NBR` parity result: `Not used in current release shape; QA query returned 4,184 flag mismatches because the snapshot intentionally leaves this field null`
- Notes:
  - batch provenance from the latest `CI_FT_PROC` row per `FT_ID` matched exactly for populated batch code and batch number
  - latest-batch auto-flagging is a manual/report-side decision in the current implementation

## Description And Lookup Coverage
- FT type description mismatches: `0`
- GL distribution status description mismatches: `0`
- Distribution code description mismatches: `0`
- GL division description mismatches: `0`
- SA status description mismatches: `0`
- SA type description mismatches: `0`
- Bill cycle description mismatches: `0`
- Customer class description mismatches: `0`
- Collection class description mismatches: `0`
- Account management group description mismatches: `0`
- Balance control status mismatches: `0`
- Bill segment description mismatches: `0`
- Adjustment description mismatches: `0`
- Freeze user name mismatches: `0`
- Source lookup gaps found:
  - `DST_ID`: `77`
  - `SA_TYPE_CD`: `52`
  - `BILL_CYC_CD`: `1,353`
  - `ACCT_MGMT_GRP_CD`: `4,954,576`
  - `BSEG_BILL_CYC_CD`: `42,768`
  - `BSEG_CAN_RSN_CD`: `2,161,849`
  - `ADJ_TYPE_CD`: `70`
  - `ADJ_CAN_RSN_CD`: `544,862`
- Notes:
  - mismatch counts are `0`, so snapshot descriptions match the source lookup outcome exactly where lookups exist
  - remaining issues are source lookup coverage, not snapshot logic defects

## Raw-Code-Only Business Fields
- `CURRENCY_CD` include with description?: `Keep in snapshot for traceability; no business decode required at this stage`
- `CIS_DIVISION` include with description?: `Keep in snapshot for traceability; only expose if business confirms it is a real reporting dimension`
- `CHAR_TYPE_CD` include with description?: `Keep in snapshot; technical unless a specific characteristic reporting need is approved`
- switch fields include with description?: `Keep in snapshot for debugging and audit trace; do not treat as required end-user dimensions`
- `BATCH_CD` and `BATCH_NBR` include with description?: `Keep in snapshot as operational provenance fields; no additional decode required`
- `IS_LATEST_BATCH_NBR` include with description?: `Keep reserved if needed by future reporting, but do not rely on it in the current release`
- Fields excluded from end-user surface: `None documented as excluded in current run`
- Reason for exclusion: `N/A`
- Technical-only fields retained in snapshot but hidden in Domain:
  - recommended candidates if Domain cleanup is desired later:
    - `CURRENCY_CD`
    - `CIS_DIVISION`
    - `CHAR_TYPE_CD`
    - `TOT_AMT_SW`
    - `FREEZE_SW`
    - `XFERRED_OUT_SW`
    - `CORRECTION_SW`
    - `NEW_DEBIT_SW`
    - `SHOW_ON_BILL_SW`
    - `NOT_IN_ARS_SW`

## Utility / Business Context Decision Log
- Population boundary decision: `Include all CI_FT_GL rows tied to non-redundant FT rows where CI_FT.REDUNDANT_SW = 'N'`
- Included FT families: `AD`, `AX`, `BS`, `BX`, `PS`, `PX`
- Included GL attributes:
  - `GL_ACCT`
  - `DST_ID` / `DST_DESC`
  - `GL_AMOUNT`
  - `STATISTIC_AMOUNT`
  - FT header, SA/account, balance-control-group, bill segment, adjustment, and payment overlays
- Excluded utility/business fields: `No numeric-truth fields excluded from the snapshot`
- Schema features not used in this tenant:
  - maintained `ACCT_MGMT_GRP` translation appears absent
  - some cancellation-reason and bill-cycle lookup populations are incomplete
- Action taken on unused features:
  - keep technical/source fields in snapshot for traceability
  - treat missing descriptions as documented source lookup gaps, not as reasons to reject the snapshot

## Sample Evidence
- Attach or paste key query outputs:
  - source/snapshot GL line parity: `4,954,576 / 4,954,576`
  - distinct `FT_ID` parity: `2,322,703 / 2,322,703`
  - `STATISTIC_AMOUNT` parity: `475,046,395 / 475,046,395`
  - FT-type-level parity passed across all six FT families
  - batch parity passed for `BATCH_CD` and `BATCH_NBR`; latest-batch flag mismatches: `4,184` expected under current null-flag design
- Attach anti-join samples if non-zero: `None; both anti-join checks returned 0`
- Attach raw-code sample rows if any:
  - sample rows confirmed technical fields like `CURRENCY_CD`, `CIS_DIVISION`, `CHAR_TYPE_CD`, and switch flags are populated for trace/debug use
  - no numeric discrepancy was tied to these fields

## Final Decision
- Promote as-is: `Yes`
- Needs column additions: `No`
- Needs lookup additions: `Optional source-data remediation only; not a snapshot blocker`
- Needs population change: `No`
- Needs documentation update: `Completed; keep source lookup exceptions noted in ongoing release documentation`
