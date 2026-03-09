# Index Coverage: Usage/Billing Financial Domains

Scope: six updated domains
- `Usage_Billing_Financial_Bridge_PerfFast_6M.xml`
- `Usage_Billing_Financial_Bridge_No_Derived_UltraSafe.xml`
- `Billed_Revenue_By_Rate_Component_Perf_6M.xml`
- `Billed_Revenue_Tax_Lean_Perf_6M.xml`
- `Billed_Usage_Consumption_Billed_Amount_Perf_6M.xml`
- `Billed_Usage_Consumption_Billed_Amount_UltraLean.xml`

Notes:
- Core sources `C1_BI_BILLED_USAGE_VW` and `C1_BI_FT_VW` are views; index behavior depends on base tables/materialization.
- List below is from local extracted dictionary (`output/cisadm_dictionary/index_columns_enriched.csv`).

## Key Join/Filter Indexes Present

### Billing/account/status lookups
- `CI_ACCT`
  - `XM148P0 (ACCT_ID)`
  - `XM148S1 (BILL_CYC_CD, ACCT_ID)`
- `CI_BILL`
  - `XT033P0 (BILL_ID)`
  - `XT033S1 (ACCT_ID, BILL_STAT_FLG, BILL_CYC_CD, WIN_START_DT)`
  - `CM_XT112S3 (BILL_STAT_FLG, ACCT_ID, BILL_ID)`
- `CI_BSEG`
  - `XT048P0 (BSEG_ID)`
  - `XT048S1 (BILL_ID)`
  - `XT048S2 (SA_ID)`
- `CI_SA`
  - `XM199P0 (SA_ID)`
  - `XM199S1 (ACCT_ID, SA_STATUS_FLG)`
  - `CM_XM199S1 (CIS_DIVISION, SA_TYPE_CD)`
- `CI_LOOKUP_VAL_L`
  - `XC353P0 (FIELD_NAME, FIELD_VALUE, LANGUAGE_CD)` (ideal for status/code description joins)
- `CI_BILL_CYC_L`
  - `XC338P0 (BILL_CYC_CD, LANGUAGE_CD)`
- `CI_CUST_CL_L`
  - `XC523P0 (CUST_CL_CD, LANGUAGE_CD)`
- `CI_COLL_CL_L`
  - `XC513P0 (COLL_CL_CD, LANGUAGE_CD)`
- `CI_RS_L`
  - `XC568P0 (RS_CD, LANGUAGE_CD)`
- `CI_SA_TYPE_L`
  - `XC571P0 (CIS_DIVISION, SA_TYPE_CD, LANGUAGE_CD)`

### Rate component path
- `CI_BSEG_CALC`
  - `XT072P0 (BSEG_ID, HEADER_SEQ)`
- `CI_BSEG_CALC_LN`
  - `XT050P0 (BSEG_ID, HEADER_SEQ, SEQNO)`
- `CI_RC`
  - `XC179P0 (RS_CD, EFFDT, RC_SEQ)` (effective-dated RC resolution)
- `CI_RC_L`
  - `XC561P0 (RS_CD, EFFDT, RC_SEQ, LANGUAGE_CD)`
- `D1_UOM_L`
  - `D1C126P0 (D1_UOM_CD, LANGUAGE_CD)`
- `D1_TOU_L`
  - `D1C128P0 (D1_TOU_CD, LANGUAGE_CD)`
- `D1_SQI_L`
  - `D1C130P0 (D1_SQI_CD, LANGUAGE_CD)`

## Read-Only Live Verification Query

Run this in each environment to verify index coverage directly in DB:

```sql
SELECT index_name, table_name, column_name, column_position
FROM all_ind_columns
WHERE owner = 'CISADM'
  AND table_name IN (
    'CI_ACCT','CI_BILL','CI_BSEG','CI_SA',
    'CI_LOOKUP_VAL_L','CI_BILL_CYC_L','CI_CUST_CL_L','CI_COLL_CL_L',
    'CI_RS_L','CI_SA_TYPE_L',
    'CI_BSEG_CALC','CI_BSEG_CALC_LN','CI_RC','CI_RC_L',
    'D1_UOM_L','D1_TOU_L','D1_SQI_L'
  )
ORDER BY table_name, index_name, column_position;
```

## Action if Slow Queries Persist

1. Validate that `ACCOUNTING_DT` predicates in view-based queries prune to recent partitions.
2. Validate join selectivity on `(BSEG_ID,UOM_CD,TOU_CD,SQI_CD)` in rate-component queries.
3. If runtime remains high after partition pruning, raise DBA request for:
   - review of view definitions for `C1_BI_BILLED_USAGE_VW` and `C1_BI_FT_VW`
   - possible supporting index strategy on underlying large fact tables.
