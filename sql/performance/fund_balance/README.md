# Fund Balance SQL Pack

Purpose:
- Provide explicit, read-only SQL for fund balance / GL verification.
- Mirror the dataset currently consumed by General Ledger Domain-based JRXML reports.

Why this exists:
- The GL reports are currently `language="domain"` and point to:
  - `/SmartCity/Report/Workstreams/Finance/General_Ledger/General_Ledger___Domain`
- This pack gives direct SQL you can run to verify location, data, and logic outside the domain engine.

Primary objects:
- `CISADM.C1_BI_FTGL_VW` (view-based GL line source)
- `CISADM.CI_FT_GL` + `CISADM.CI_FT` (raw reconciliation source)
- `CISADM.CI_FT_PROC` (batch number)
- `CISADM.CI_DST_CODE_EFF` (maps `DST_ID` + `GL_ACCT` to `FUND_CD`)
- `CISADM.CI_FUND` + `CISADM.CI_FUND_L` (fund code and fund description)
- `CISADM.CI_LOOKUP_VAL_L` (status/type descriptions)
- `CISADM.CI_ACCT`, `CISADM.CI_ACCT_PER`, `CISADM.CI_PER_NAME`, `CISADM.CI_PREM` (customer/address context)

Files:
- `fund_balance_batch_detail.sql`
  - Row-level dataset aligned to GL report query fields, including fund code/description lookups.
- `fund_balance_latest_batch_summary.sql`
  - Executive metrics (row counts, bad rows, amount totals), including missing fund-map count.
- `fund_balance_account_gl_rollup.sql`
  - Rollup by account + GL account + fund for targeted account verification.
- `fund_balance_view_vs_raw_reconciliation.sql`
  - Reconciliation of `C1_BI_FTGL_VW.FT_GL_AMT` vs `CI_FT_GL.AMOUNT` by GL account + fund.

Domain design file:
- `domains/working/manual_designs/Fund_Balance_No_Derived_With_Fund_Lookups.xml`
  - Importable Domain design XML (no derived tables) with lookup/description joins for fund names.

Common parameters:
- `:P_START_ACCOUNTING_DT` (optional)
- `:P_END_ACCOUNTING_DT` (optional)
- `:P_BATCH_NBR` (optional)
- `:P_ONLY_LATEST_BATCH` (`'Y'`/`'N'`)
- `:P_ACCT_ID_LIST` (optional comma-separated account list)

Additional parameter in detail query:
- `:P_ONLY_EXCEPTIONS` (`'Y'`/`'N'`)
- `:P_MIN_ABS_AMOUNT` (optional)

Read-only guarantee:
- All files are `SELECT`-only.
- No DDL/DML or session mutation statements.
