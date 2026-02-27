# Billing Cycle Reporting Semantics

## Definitions
- Expected active SA: active SA assigned to a billing cycle via account (`CI_ACCT.BILL_CYC_CD`).
- Actual billed SA: SA appearing in `CI_BSEG` in the selected event scope.
- Latest event per cycle: max `TRUNC(NVL(CI_BILL.BILL_DT, CI_BSEG.CRE_DTTM))` for each cycle.
- Most recent cycle (global): cycle with the greatest latest-event date across all cycles.

## Report Roles
1. Actual Snapshot report:
   - answers "what happened" in latest event per cycle.
2. Drill-down report:
   - answers "which bill/segment rows and statuses are involved."
3. Expected vs Actual report:
   - answers "what should have happened vs what happened."

## Interpretation Rules
- `BILL_SEGMENT_COUNT` can be greater than `BILL_COUNT` due to multiple segments per bill.
- Large expected vs actual gaps are not automatically data defects:
  - may indicate cycle timing/partial run windows.
- Always interpret counts together with cycle latest-event date.

## Flags
- `MOST_RECENT_BILL_CYCLE_SW`:
  - Y for globally latest cycle, N for others.
- `IS_ERROR_SW`:
  - Y when status description indicates error-like condition.

## Client Communication Guidance
- Say "latest event snapshot" explicitly.
- Avoid presenting snapshot values as full-month/full-cycle totals unless stated.
