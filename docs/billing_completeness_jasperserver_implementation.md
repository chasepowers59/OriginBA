# Billing Completeness in Jasper Domain Designer (No WITH)

## Why this approach
Jasper Domain derived tables often reject `WITH` CTE syntax.  
Use inline `SELECT ... FROM (SELECT ...)` queries instead.

## Use This SQL
Preferred for Domain Designer parser stability:
- `sql/derived_billing_completeness_summary_select_only.sql`
- `sql/derived_billing_completeness_detail_select_only.sql`

These files are:
1. Single `SELECT` only
2. No `WITH`
3. No trailing semicolon
4. Aligned to current Bill Segment domain join tree (`CI_BILL -> CI_BSEG -> CI_ACCT` + lookup/description tables)
5. Segment-centric metrics (`BSEG_ID`) for multi-service accounts

It provides:
1. Cycle summary reconciliation query
2. Exception detail query

## Implementation Steps (Domain)
1. Open Domain Designer for your billing domain project.
2. Add a **Derived Table** for summary by pasting:
   - `sql/derived_billing_completeness_summary_select_only.sql`
3. Add a second **Derived Table** for detail by pasting:
   - `sql/derived_billing_completeness_detail_select_only.sql`
4. Expose fields:
   - Summary: `BILL_CYCLE_CODE`, `BILL_CYCLE_DESCRIPTION`, `BILL_DATE`, `BILL_CREATE_DATE`, `GENERATED_BILL_COUNT`, `GENERATED_BILL_SEGMENT_COUNT`, `DISTINCT_PREMISE_COUNT`, `BILLS_WITHOUT_SEGMENT_COUNT`, `EXPECTED_BILL_SEGMENT_COUNT`, `MISSING_BILL_SEGMENT_COUNT`, `BILL_SEGMENT_COMPLETION_PCT`
   - Detail: `BILL_CYCLE_CODE`, `BILL_CYCLE_DESCRIPTION`, `BILL_DATE`, `BILL_CREATE_DATE`, `BILL_SEGMENT_CREATE_DATE`, `EVENT_DATE_FOR_FILTER`, `ACCOUNT_ID`, `SERVICE_AGREEMENT_ID`, `PREMISE_ID`, `BILL_ID`, `BILL_SEGMENT_ID`, `BILL_STATUS_DESCRIPTION`, `BILL_SEGMENT_STATUS_DESCRIPTION`, `RECONCILIATION_RESULT`
5. Create domain filters (recommended):
   - `BILL_CYCLE_CODE`
   - `BILL_DATE`
   - `BILL_CREATE_DATE` or `BILL_SEGMENT_CREATE_DATE` (creation date mode)
   - `RECONCILIATION_RESULT` (`MISSING_BSEG`, `ORPHAN_BSEG`, `PRESENT`)
6. Publish to `Origin_DEV` and test.

## Recommended Report Pair
1. `billing_cycle_completion_monitor` (from summary derived table)
2. `billing_missing_bill_exceptions` (from detail derived table)
   - Detail layout now includes `EXCEPTION_TYPE` so operators can distinguish missing-bill, missing-segment, orphan-segment, and status-exception rows without opening the raw domain.

## Business-Friendly Field Names Included
The SQL aliases are already business-oriented, including:
- `BILL_CYCLE_CODE`, `BILL_CYCLE_DESCRIPTION`
- `BILL_DATE`, `BILL_CREATE_DATE`
- `GENERATED_BILL_COUNT`, `GENERATED_BILL_SEGMENT_COUNT`
- `EXPECTED_BILL_SEGMENT_COUNT`, `MISSING_BILL_SEGMENT_COUNT`, `BILL_SEGMENT_COMPLETION_PCT`
- `BILL_STATUS_CODE`, `BILL_STATUS_DESCRIPTION`
- `BILL_SEGMENT_STATUS_CODE`, `BILL_SEGMENT_STATUS_DESCRIPTION`
- `RECONCILIATION_RESULT`

## Code/Description Coverage
Included in detail query:
1. Bill Cycle description from `CI_BILL_CYC_L`
2. Bill status description from `CI_LOOKUP_VAL_L` (`FIELD_NAME='BILL_STAT_FLG'`, `LANGUAGE_CD='ENG'`)
3. Bill segment status description from `CI_LOOKUP_VAL_L` (`FIELD_NAME='BSEG_STAT_FLG'`, `LANGUAGE_CD='ENG'`)

## Validation Procedure
1. Filter summary to last night by `BILL_DATE` or `BILL_CREATE_DATE` as needed.
2. Verify completion % and missing count against batch control totals.
3. Open exception report and spot-check 10 records in C2M UI.
4. Confirm no false positives for closed/inactive SA logic.

## Known Tuning Points
1. `active_sa_status` value is client-specific.
2. Date field for BSEG inclusion can vary (`CRE_DTTM` vs segment period dates).
3. If volume is high, pre-stage into a nightly reconciliation table and domain off that table.
4. Current "expected" denominator is one segment-bearing check per generated Bill (`BILLS_WITHOUT_SEGMENT_COUNT`).
5. Some tenants store blank/space `BILL_CYC_CD`; SQL normalizes this to `UNASSIGNED`.
