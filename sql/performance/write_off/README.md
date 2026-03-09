# Write-Off Analytics SQL Pack

Purpose:
- Provide read-only analytics for write-off process volume, debt, effectiveness, and duration trends.
- Date window is hard-coded to recent months:
  - Process start date `>= DATE '2025-09-01'`
  - Payment date filter in payment-estimate query `>= DATE '2025-09-01'`
- Optional account targeting parameter across queries:
  - `:P_ACCT_ID_LIST` (comma-separated `ACCT_ID` list)

Primary source:
- `CISADM.C1_BI_WOPROC_VW` (dedicated write-off BI view; avoids mixed non-write-off collection processes).

Key field mapping:
- `PROC_ID` -> `UNCOLL_PROC_ID`
- `ACCT_ID` -> `ACCT_ID`
- `START_DT` -> `CRE_DTTM`
- `STATUS_CD` -> `WO_STATUS_FLG` and/or `UNCOLL_PROC_STAT_FLG`
- `INIT_OUTSTANDING_AMT` -> `ARS_AT_START`
- `AMOUNT_RECOVERED` (estimated) -> `GREATEST(ARS_AT_START - ARS_AT_END, 0)`
- `DAYS_TO_CLOSE` -> `UNCOLL_PROC_DUR` (or date diff proxy)
- `CLOSE_DT` -> `WO_PROC_COMPL_DT`

Important caveats:
- `AMOUNT_WRITTEN_OFF` is not exposed as a direct column in this view.
- Payment-based recovery is provided as an estimate using `CI_COLL_PROC_SA -> CI_PAY_SEG -> CI_PAY_TNDR -> CI_PAY_EVENT`.
- Status code semantics should be validated per tenant using lookups before final KPI governance.

Files:
- `write_off_active_snapshot.sql`
- `write_off_creation_trend.sql`
- `write_off_effectiveness_trend.sql`
- `write_off_duration_trend.sql`
- `write_off_recovery_post_init_payments_est.sql`
- `write_off_account_detail.sql`
