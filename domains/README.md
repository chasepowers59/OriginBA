# Domain Packaging Layout

- `exports/`: import-ready Jaspersoft domain ZIP packages.
- `working/`: local extracted copies for safe domain editing and validation.

Keep production-safe artifacts in `exports/`; use `working/` for temporary edits only.

## Active Manual Design XML (Standard Set)

- `working/manual_designs/Billed_Usage_Consumption_Billed_Amount_Perf_6M.xml`
- `working/manual_designs/Billed_Usage_Consumption_Billed_Amount_UltraLean.xml`
- `working/manual_designs/Billed_Revenue_By_Rate_Component_Perf_6M.xml`
- `working/manual_designs/Billed_Revenue_Tax_Lean_Perf_6M.xml`
- `working/manual_designs/Usage_Billing_Financial_Bridge_PerfFast_6M.xml`
- `working/manual_designs/Usage_Billing_Financial_Bridge_No_Derived_UltraSafe.xml`
- `working/manual_designs/Fund_Balance_Final_DB_Validated.xml`
- `working/manual_designs/Fund_Balance_Monthly_PerfSafe.xml`
- `working/manual_designs/Write_Off_Requirements_Final_DB_Validated.xml`
- `working/manual_designs/Billing_Requirements_No_Derived_Full_Logic.xml`
- `working/manual_designs/Unbilled_Revenue_Snapshot_Perf.xml`
- `working/manual_designs/Collections_Process_Effectiveness_Debt_Reduction_180D.xml`
- `working/manual_designs/D1_Usage_Device_Account_Outlier_180D.xml`
- `working/manual_designs/To_Do_Entry_Operations_Account_Resolved.xml`

## Archived Manual Design XML

- Legacy and duplicate variants are in:
- `working/archive/manual_designs/`

## Domain Business Catalog

- Business-purpose and use-case summary for each domain:
- `working/manual_designs/DOMAIN_BUSINESS_CATALOG.md`
- One-page domain chooser for business users:
- `working/manual_designs/DOMAIN_DECISION_MATRIX.md`

## Bill Cycle Domain (New Bill Cycle Domain.zip)

- Updated domain model now includes:
- `BC_CYCLE_NUMBERS_FAST`
- `BC_EXPECTED_VS_ACTUAL_FAST`
- `BC_SEGMENT_STATUS_DRILLDOWN_V2`
- Primary verification fields now cover expected vs actual billing totals, detailed bill and bill segment status, and error flags (`IS_ERROR_SW`, `ERROR_REASON`).
- Datasource resources are intentionally excluded from `New Bill Cycle Domain.zip`; imports bind to existing repository alias/reference only.
- Read-only Oracle index inspection confirms key lead-index prefilter columns in this area are mostly IDs/cycle keys, not `CI_BSEG.CRE_DTTM`.
- Recommended ad hoc prefilters for performance:
- `BILL_CYCLE_CODE` (from `CI_BILL_CYC_L.BILL_CYC_CD`)
- Optional equality/IN filters on account/service identifiers for drilldown use cases.
- Date windows are still included in derived queries to cap scan volume, but should not be treated as lead-index filters for these specific billing tables.
