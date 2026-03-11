# Billing Verification v2 Validation Runbook

## Purpose
Use this runbook to validate the `Billing_Requirements_Domain_v2` logic in Oracle before or after importing the domain into JasperReports Server.

## Source Files
- Summary parity query: `sql/reconciliation/billing/billing_verification_v2_summary_oracle.sql`
- Detail parity query: `sql/reconciliation/billing/billing_verification_v2_detail_oracle.sql`
- Source-field probe: `sql/reconciliation/billing/billing_verification_v2_cycle_source_probe.sql`
- Domain working package: `domains/working/billing_requirements_domain_v2`
- Business-facing report: `reports/billing_verification_flow.jrxml`

## What v2 Is Doing
- Expected population comes from active service agreements on accounts using `CI_ACCT.BILL_CYC_CD`.
- Latest cycle snapshot comes from the max event date per cycle across `CI_BILL` and `CI_BSEG`.
- Bill counts and billed accounts come from `CI_BILL`.
- Billed service agreements and segment counts come from `CI_BSEG`.
- Exception detail includes:
  - `MISSING_EXPECTED_BILL`
  - `MISSING_BSEG`
  - `ORPHAN_BSEG`
  - `BILL_STATUS_EXCEPTION`
  - `BSEG_STATUS_EXCEPTION`

## Validation Sequence
1. Run `billing_verification_v2_cycle_source_probe.sql`.
2. Review any cycle with non-zero `mismatch_count`.
3. Run `billing_verification_v2_summary_oracle.sql`.
4. Pick one or two bill cycles from that output, especially the most recent cycle and one cycle with gaps.
5. Run `billing_verification_v2_detail_oracle.sql`.
6. Filter the detail result to the same bill cycle codes you picked from the summary output.
7. Import or refresh `Billing_Requirements_Domain_v2` in JRS.
8. Run `billing_verification_flow.jrxml` with `MOST_RECENT_ONLY=true`.
9. Export the report to CSV or XLSX.
10. Compare the report cycle counts and exception rows to the Oracle query outputs.

## What Should Match
- `BILL_CYCLE_CODE`
- `BILL_CYCLE_DESCRIPTION`
- `EXPECTED_ACTIVE_SA_COUNT`
- `EXPECTED_ACTIVE_ACCOUNT_COUNT`
- `ACTUAL_BILLED_SA_COUNT`
- `ACTUAL_BILLED_ACCOUNT_COUNT`
- `ACTUAL_BILL_SEGMENT_COUNT`
- `ACTUAL_BILL_COUNT`
- `MISSING_ACTIVE_SA_COUNT`
- `MISSING_ACTIVE_ACCOUNT_COUNT`
- `RECON_CYCLE_LAST_EVENT_DATE`

## How To Confirm The Report Is Correct
- The cycle shown as most recent in Oracle should be the same cycle shown when `MOST_RECENT_ONLY=true`.
- Every summary count shown in the report should match the Oracle summary query for the same cycle.
- Every exception row shown in the report should exist in the Oracle detail query for the same cycle.
- A bill cycle with `MISSING_ACTIVE_ACCOUNT_COUNT > 0` should have at least one `MISSING_EXPECTED_BILL` or another actionable exception explaining the gap.
- `MISSING_BSEG` rows should have a `BILL_ID` but no `BILL_SEGMENT_ID`.
- `ORPHAN_BSEG` rows should have a `BILL_SEGMENT_ID` and may have no matching bill header in the latest snapshot.

## If Results Do Not Match
- If the summary counts differ:
  - confirm the domain imported is `Billing_Requirements_Domain_v2`, not the old domain
  - confirm the report URI points to the v2 domain
  - confirm the JRS export is filtered the same way as your Oracle run
- If the detail rows differ:
  - compare the latest cycle date first
  - then compare `BILL_ID`, `BSEG_ID`, and `ACCOUNT_ID`
  - then review cycle-source mismatches from the probe query
- If the source probe shows large mismatch counts:
  - review whether the environment relies more on account cycle assignment, bill header cycle code, or bill segment cycle code for that client
  - if mismatch is systematic, adjust the resolved cycle-code rule before promoting

## Promotion Note
Do not promote the report update until the JRS domain import is complete. The report source now expects `/SmartCity/Report/Workstreams/Billing_and_Rates/Bill_Segment/Billing_Requirements_Domain_v2`.
