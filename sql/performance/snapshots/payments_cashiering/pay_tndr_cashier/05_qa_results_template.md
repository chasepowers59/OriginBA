# PAY_TNDR_CASH_RPT_CURR QA Results

## Run Metadata
- Environment: `DEV` (user-run in SQL Developer)
- Run date: `2026-04-13`
- Run by: User in SQL Developer; results documented in repo by Codex
- Snapshot object: `CISADM.PAY_TNDR_CASH_RPT_CURR`
- Validation SQL used:
  - `04_validation_queries.sql`

## Summary
- Pass / Fail: `Pass`
- Ready for ad hoc use: `Yes`
- Key blockers: `None for tender-grain parity or additive tender truth`
- Residual risks:
  - staged tender source rows can exist outside the governed base `CI_PAY_TNDR` population and should not be interpreted as snapshot misses
  - event-level and deposit-level overlay amounts repeat across multiple tender rows by design and must not be treated as additive tender-grain truth

## Population Boundary Decision
- Included tenders: `All rows from CISADM.CI_PAY_TNDR`
- Excluded tenders: `No base tenders are intentionally excluded`
- Reason: `The snapshot is the governed tender-centered payment intake layer and is meant to preserve one row per base tender`

## Source Parity
- Source tender count: `648,916`
- Snapshot tender count: `648,916`
- Count difference: `0`
- Source rows missing in snapshot: `0`
- Snapshot rows not in source: `0`
- Source `TENDER_AMT` total: `1.2579E+10`
- Snapshot `TENDER_AMT` total: `1.2579E+10`
- `TENDER_AMT` difference: `0`

## Description And Lookup Coverage
- Tender type description missing rows: `0`
- Tender source description missing rows: `0`
- Event pay status description missing rows: `0`
- Auto-pay source name missing rows: `0`
- Source family description missing rows: `0`
- Customer name missing rows: `0`

## Stage And Control Coverage
- Staged tender rows in snapshot: `1,547`
- Staged tender rows joining base tender: `1,547`
- Orphan staged rows not in base tender: `1`
- Missing tender control IDs: `0`
- Missing deposit control IDs: `0`
- Notes:
  - staged tender linkage matches the governed base tender population exactly
  - the single orphan staged row exists in `CI_PAY_TNDR_ST` without a matching `CI_PAY_TNDR` row and is therefore not a snapshot defect

## Source Family Classification
- `ACH` rows not classified `LEGACY_APAY`: `0`
- `ORIGINP` / OriginPay tender rows not classified `ORIGINPAY`: `0`
- Derived source family profile:
  - `ORIGINPAY`: `162,408` rows, `1.2390E+10`
  - `LEGACY_APAY`: `375,155` rows, `134,005,741`
  - `OTHER`: `109,806` rows, `54,520,147.6`
  - `STAGED_EXTERNAL`: `1,547` rows, `435,846.22`

## Raw-Code-Only Business Fields
- Code-only business fields requiring translation?: `None identified as release blockers in this QA pack`
- Fields excluded from end-user surface: `None required for numeric acceptance`
- Reason for exclusion: `N/A`

## Utility / Business Context Decision Log
- Included tender truth fields: `PAY_TENDER_ID`, `PAY_DT`, `TENDER_AMT`, tender type, tender status, tender source, and source-family classification`
- Included overlay fields: `event-level payment summary, event-level tender summary, pay-segment summary, tender control, deposit control, staged external-source context, and customer context`
- Excluded lower-grain detail: `raw row-per-pay-segment application detail, debt logic, and FT / GL accounting detail`
- Action taken on repeated overlays: `documented as contextual only; not to be summed as tender-grain truth`

## Final Decision
- Promote as-is: `Yes`
- Needs lookup additions: `No`
- Needs population change: `No`
- Needs documentation update: `Completed; master technical guide added for this snapshot`
