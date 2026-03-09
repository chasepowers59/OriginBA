# Usage-Billing-Financial Bridge Domain Plan

## Objective
Bridge usage quantity and billed amount with financial posting amounts in one domain design, using read-only objects and no derived tables.

## Recommended Grain
- Primary grain: `BILL_ID + BSEG_ID + RS_CD`
- Reason: this is the safest common key between:
  - `C1_BI_BILLED_USAGE_VW` (usage/billed amount side)
  - `C1_BI_FT_VW` (financial amount side)

## Domain Designs Delivered
- `domains/working/manual_designs/Usage_Billing_Financial_Bridge_No_Derived_UltraSafe.xml`
- `domains/working/manual_designs/Usage_Billing_Financial_Bridge_No_Derived_Core.xml`

## Join Tree (Core)
1. Base: `C1_BI_BILLED_USAGE_VW`
2. Left join financials:
   - `C1_BI_BILLED_USAGE_VW.BILL_ID = C1_BI_FT_VW.BILL_ID`
   - `C1_BI_BILLED_USAGE_VW.BSEG_ID = C1_BI_FT_VW.BSEG_ID`
   - `C1_BI_BILLED_USAGE_VW.RS_CD = C1_BI_FT_VW.RS_CD`
3. Left join bill header:
   - `C1_BI_BILLED_USAGE_VW.BILL_ID = CI_BILL.BILL_ID`
4. Left join bill segment:
   - `C1_BI_BILLED_USAGE_VW.BSEG_ID = CI_BSEG.BSEG_ID`
5. Left join service agreement:
   - `C1_BI_BILLED_USAGE_VW.SA_ID = CI_SA.SA_ID`
6. Left join status lookups:
   - Bill status: `BILL_STAT_FLG`
   - Bill segment status: `BSEG_STAT_FLG`
   - SA status: `SA_STATUS_FLG`
   - FT type: `FT_TYPE_FLG`

## Performance Prefilter
- Pushdown prefilter in both delivered XMLs via `jdbcQuery` for `C1_BI_BILLED_USAGE_VW`:
- `ACCOUNTING_DT >= add_months(trunc(sysdate), -6)`
- `ACCOUNTING_DT < trunc(sysdate) + 1`
  - `BILL_ID is not null`
  - `BSEG_ID is not null`
  - `RS_CD is not null`
- Aggregated FT query (`C1_BI_FT_VW_AGG`) also applies key null guards and the same date window.
- This bounds row volume before runtime joins and reduces low-value null-key row scans.

## Key Measures
- Usage side:
  - `TOTAL_BILLED_USAGE_QTY`
  - `TOTAL_BILLED_USAGE_AMT`
- Financial side:
  - `TOTAL_FT_GL_REV_AMT`
  - `TOTAL_FT_GL_TAX_AMT`
  - `TOTAL_FT_OTHER_AMT`
  - `TOTAL_FT_TOT_AMT`

## Ad Hoc Build Pattern (to avoid double counting)
1. Use row grouping at least by:
   - `Bill ID`, `Bill Segment ID`, `Rate Schedule Code`
2. Add measures:
   - `Total Billed Usage Quantity`
   - `Total Billed Usage Amount`
   - `Total FT GL Revenue Amount`
   - `Total FT GL Tax Amount`
3. Add filters:
   - `Billed Usage Accounting Date` range
   - Optional: `Bill Status Description = Complete`

## Rollout Sequence
1. Import `UltraSafe` first and validate.
2. If stable, import `Core` for richer status/description context.
3. Save a backup export before each import.
