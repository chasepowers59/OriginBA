# CityCorp Billing Cycle Reporting Plan

## Objective
Build a production-ready Jaspersoft reporting package for CityCorp that answers:
- What billing activity occurred in the latest event per bill cycle?
- Which bill segments are in error and why?
- How does actual billed population compare to expected active population?

## End Goal
Deliver three coordinated reports (derived tables) that provide:
- Executive cycle-level snapshot (actuals).
- Operational drill-down to bill/segment status and error rows.
- Reconciliation of expected vs actual for completeness analysis.

## Report Set
1. Actual Snapshot Report  
Path: `sql/performance/bill_cycle/bill_cycle_numbers_single_report_query.sql`  
Purpose: cycle-level counts at latest event per cycle.

2. Segment Drill-Down Report  
Path: `sql/performance/bill_cycle/bill_cycle_segment_status_drilldown.sql`  
Purpose: row-level bill segment detail, bill/segment status, error flag/reason.

3. Expected vs Actual Reconciliation Report  
Path: `sql/performance/bill_cycle/bill_cycle_expected_vs_actual_reconciliation.sql`  
Purpose: compare expected active SA/account population vs actual billed SA/account population.

## Required Tables
- `CISADM.CI_BSEG`
- `CISADM.CI_BILL`
- `CISADM.CI_SA`
- `CISADM.CI_ACCT`
- `CISADM.CI_BILL_CYC_L`
- `CISADM.CI_LOOKUP_VAL_L`

## Core Business Logic
- Bill cycle source is `CI_BSEG.BILL_CYC_CD` (authoritative for billed activity).
- Active service agreements are `NULLIF(TRIM(CI_SA.SA_STATUS_FLG), '') = '20'`.
- Latest event per cycle is `MAX(TRUNC(NVL(CI_BILL.BILL_DT, CI_BSEG.CRE_DTTM)))` by cycle.
- Snapshot and drill-down only use rows where `EVENT_DATE = CYCLE_LAST_EVENT_DATE`.
- Error detection is based on status description text containing `ERROR|EXCEPTION|FAIL|CANCEL`.

## In Scope
- Latest-event-per-cycle reporting.
- Bill and segment status enrichment (lookup descriptions).
- Error-only filtering in drill-down (`IS_ERROR_SW = 'Y'` at report/filter layer).
- Most recent cycle Y/N flag.
- Cross-environment operability without hardcoded cycle lists.

## Out of Scope
- Retroactive full-history cycle trend analytics.
- Device usage logic (`D1_USAGE*`) and usage-to-SA mapping paths.
- Guaranteed root-cause exception message text from custom exception tables not yet validated per environment.
- Billing orchestration diagnostics outside report data model.

## Validation and Test Plan
1. Schema/availability checks
- Confirm required tables/columns exist in target environment.
- Confirm row availability for `CI_BSEG`, `CI_BILL`, `CI_SA`, `CI_ACCT`.

2. Logic validation SQL
- Run `sql/performance/bill_cycle/bill_cycle_active_validation.sql` to confirm summary vs drill-down parity.
- Run `sql/performance/bill_cycle/bill_cycle_jaspersoft_parity_check.sql` to compare DB totals/fingerprints against Jasper export.

3. Reconciliation sanity checks
- Validate expected vs actual values by cycle with known samples.
- Confirm low/zero activity cycles align with actual latest cycle event dates.

4. Jasper UAT checks
- Derived table parses successfully in Domain Designer.
- Filters produce expected behavior:
- `MOST_RECENT_BILL_CYCLE_SW = 'Y'` returns globally newest cycle.
- `IS_ERROR_SW = 'Y'` returns only error rows in drill-down.
- Aggregations in report are set to `SUM` (not `COUNT`) for measure fields.

5. Signoff criteria
- Count parity passes.
- Reconciliation outputs are explainable with business context.
- Client-approved sample cycle outputs match known operational results.

## Input Controls / Filter Recommendations
- `BILL_CYCLE_CODE` (text/list)
- `MOST_RECENT_BILL_CYCLE_SW` (Y/N)
- `IS_ERROR_SW` (Y/N on drill-down)
- `BILL_DATE` or `EVENT_DATE` date range (if needed in report layer)

## Key Risks and Mitigations
- Risk: confusion between latest-event snapshot vs full-cycle totals.  
Mitigation: label reports clearly as "Latest Event Snapshot".

- Risk: expected vs actual appears far apart due to timing window.  
Mitigation: anchor interpretation to cycle last event date and publish that date in report.

- Risk: lookup descriptions missing for some status codes.  
Mitigation: keep fallback display (`BILL_STATUS_<code>`, `BSEG_STATUS_<code>`).

## Value to CityCorp
- Provides a clear, auditable answer to "what billed, what failed, and what is missing".
- Improves billing operations triage with row-level error detail.
- Supports leadership reporting with cycle-level completion visibility.
- Reduces manual investigation time by linking summary, drill-down, and reconciliation views.

## Deployment Notes
- Use datasource aliases only:
- `ORIGIN_DEV_DS`
- `C2M_QA_DS`
- `C2M_PROD_DS`
- Keep organization isolation to `Origin_DEV` by default in server assets.
- Promote using the same validation scripts in each environment before signoff.
