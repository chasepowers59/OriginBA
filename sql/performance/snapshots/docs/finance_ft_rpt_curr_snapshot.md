# Finance FT Header Snapshot

## Purpose
`CISADM.FT_RPT_CURR` is the governed finance snapshot for one-row-per-financial-transaction reporting.

It is the right artifact when the business question is:
- how many financial transactions occurred
- what FT types drove dollar volume
- which accounts, service agreements, bill cycles, or service types those transactions belong to
- which transactions are adjustments, pay segments, or bill-segment-linked rows
- whether GL distribution status looks healthy at FT header grain

It is not the right artifact when the business question requires one row per GL line. Use `CISADM.FT_GL_DISTRIBUTION_RPT_CURR` for GL account, distribution code, and GL-line reconciliation analysis.

## Recommended workflow
1. Create the table with `sql/performance/snapshots/finance/ft_rpt_curr/01_create_snapshot_table.sql`.
2. Create the procedure with `sql/performance/snapshots/finance/ft_rpt_curr/02_refresh_snapshot_procedure.sql`.
3. Optionally schedule the refresh with `sql/performance/snapshots/finance/ft_rpt_curr/03_schedule_snapshot_job.sql`.
4. Run the validation suite in `sql/performance/snapshots/finance/ft_rpt_curr/04_validation_queries.sql`.
5. Build the Jaspersoft Domain or Topic from the snapshot table rather than recreating the join logic at runtime.

## Grain
One row per `CI_FT.FT_ID`.

Natural key:
- `FT_ID`

This is the most important design rule in the snapshot.

The table should remain row-safe at FT header grain even when bill-segment, adjustment, or payment fields are populated. Those child fields are optional overlays controlled by FT type. They do not change the base grain.

## Driving tables
Driving truth:
- `CISADM.CI_FT`

Context tables:
- `CISADM.CI_SA`
- `CISADM.CI_ACCT`
- `CISADM.SC_USER`

Optional FT-type-specific child tables:
- `CISADM.CI_BSEG`
- `CISADM.CI_ADJ`
- `CISADM.CI_PAY_SEG`

Lookup and translation tables:
- `CISADM.CI_LOOKUP_VAL_L`
- `CISADM.CI_SA_TYPE_L`
- `CISADM.CI_ADJ_TYPE_L`

## Source scale
The local metadata snapshot shows:
- `CI_FT`: `4,854,740` rows
- `CI_FT_GL`: `4,953,885` rows
- `CI_FT_PROC`: `2,316,563` rows

Those counts come from `output/cisadm_dictionary/tables.csv` and are useful for explaining why a flattened snapshot is preferable to repeated runtime joins for finance self-service.

The live row count for the snapshot itself should always be validated directly with:

```sql
SELECT COUNT(*) AS snapshot_row_count
FROM cisadm.ft_rpt_curr;
```

## Why this snapshot exists
Finance reporting often starts from `CI_FT`, but end-user tools do not work well when analysts have to repeatedly rebuild:
- FT header joins
- account and service-agreement context
- description lookups
- FT-type-specific child joins

That usually leads to one of two bad outcomes:
- users rebuild the same logic inconsistently in multiple domains and reports
- someone expands the subject into mixed grain by pulling in GL detail or child tables directly

`FT_RPT_CURR` fixes that by publishing a stable one-row-per-FT table with the most common finance-facing context already resolved.

## What is included
Core FT fields:
- FT ID
- FT type code and description
- accounting date
- created and freeze timestamps
- freeze user ID and display name
- current amount and payoff amount
- bill ID
- service agreement ID
- parent ID and sibling ID
- GL distribution status code and description
- account ID
- snapshot load timestamp

Service agreement and account context:
- SA status code and description
- SA type code and description
- customer class code and description
- collection class code and description
- bill cycle code and description
- account management group code and description

Bill-segment context when the FT type is bill-segment-based:
- bill segment ID
- bill segment status code and description
- bill segment start and end dates

Adjustment context when the FT type is adjustment-based:
- adjustment ID
- adjustment status code and description
- adjustment type code and description
- adjustment amount

Payment context when the FT type is pay-segment-based:
- pay segment ID
- payment ID
- pay-segment amount

## What is intentionally excluded
- GL account, distribution code, and GL-line detail
- row-per-`CI_FT_GL` analysis
- balance-control-group deep detail
- customer-person ranking logic beyond freeze-user display name
- broader customer-facing enrichment that is not necessary for FT header analysis

Those subjects either belong in `FT_GL_DISTRIBUTION_RPT_CURR` or in separate finance and customer-oriented artifacts.

## Join rules that protect the grain
The snapshot keeps FT header grain safe by applying child joins only when the FT family makes sense:
- `BS` and `BX` rows can populate bill-segment fields
- `AD` and `AX` rows can populate adjustment fields
- `PS` and `PX` rows can populate payment-segment fields

That matters because it prevents unrelated child tables from accidentally populating across the whole population and keeps optional child logic from changing the row count.

The base filter is:

```sql
WHERE ft.redundant_sw = 'N'
```

That keeps redundant FT rows out of the reporting population.

## Description strategy
This implementation uses a mixed approach:
- `FT_TYPE_FLG_DESC` is decoded with a `CASE` expression
- `GL_DISTRIB_STATUS_DESC` is decoded with a `CASE` expression
- SA status, bill-segment status, adjustment status, SA type, and adjustment type descriptions come from lookup or translation tables

That is acceptable for the current supplied implementation, but if governed lookup coverage exists for FT type or GL distribution status in the tenant, those fields can be migrated later to lookup-driven descriptions for consistency.

## Measure guidance
Trusted additive measures at FT grain:
- `CUR_AMT`: default money measure for most FT summary reporting
- `TOT_AMT`: payoff-oriented amount, only when payoff exposure is the question

Conditionally populated measures:
- `ADJ_AMT`: useful only in adjustment-focused analysis
- `PAY_SEG_AMT`: useful only in payment-segment-focused analysis

Best practice:
- use `Count of FT_ID` as the safest volume KPI
- use `Sum of CUR_AMT` as the standard dollar KPI
- avoid mixing `ADJ_AMT` and `PAY_SEG_AMT` into broad all-FT rollups without filtering to the relevant FT families

## Best use cases
- FT type volume and dollar analysis
- GL distribution status monitoring at FT header grain
- bill-cycle and service-type FT trend reporting
- account and SA trace views for adjustments, bill segments, and payments
- finance-oriented ad hoc analysis that needs one transaction per row

## Do not use for
- GL account analysis
- distribution-code analysis
- exact GL reconciliation by FT line
- any question where repeated FT headers on GL lines are required

Use `sql/performance/snapshots/docs/finance_ft_gl_distribution_snapshot.md` and `CISADM.FT_GL_DISTRIBUTION_RPT_CURR` for those subjects.

## Validation checklist
Use `sql/performance/snapshots/finance/ft_rpt_curr/04_validation_queries.sql` to validate:
- snapshot row count
- duplicate `FT_ID` rows
- null coverage for key identifiers
- description coverage
- FT type profile
- optional child coverage by FT type
- amount population by FT type
- bill-segment date sanity
- freeze-date sanity
- recent user-facing sample rows

The legacy read-only validation helper in `sql/performance/finance/ft_rpt_curr_domain_validation.sql` performs the same style of checks for the domain-backed source.

## Implementation caveats
The current supplied DDL defines several ID columns as `VARCHAR2(30)`.

Repo metadata shows some source IDs in CISADM can be wider than that. Before production rollout, validate the maximum widths in the client environment and widen these columns if needed:
- `FT_ID`
- `BILL_ID`
- `SA_ID`
- `PARENT_ID`
- `SIBLING_ID`
- `ACCT_ID`
- `BSEG_ID`
- `ADJ_ID`
- `PAY_SEG_ID`
- `PAY_ID`

The current refresh also uses `TRUNCATE` followed by a full reload. That is simple and fast, but it means:
- the table is empty during refresh
- reporting jobs should not hit the snapshot midway through a rebuild
- scheduling should happen off-hours or in a controlled reporting window

## Domain and reporting guidance
The end-user-friendly Domain export is:
- `domains/exports/manual_imports/FT_RPT_CURR_End_User_Friendly.xml`

The companion ad hoc recipe guide is:
- `docs/finance_ft_rpt_curr_adhoc_recipes.md`

Companion XML inventory:
- `sql/performance/snapshots/docs/snapshot_xml_inventory.md`

## SQL Developer runbook
For exact SQL Developer steps to inspect the table, view the current procedure, and validate the scheduler job, use:
- `sql/performance/snapshots/docs/snapshot_sqldeveloper_runbook.md` under `FT_RPT_CURR`

For the pilot no-break migration path from table-backed snapshot to materialized-view-backed storage, use:
- `sql/performance/snapshots/finance/ft_rpt_curr/05_materialized_view_cutover_runbook.md`

Recommended default report prompt set:
- accounting date
- financial transaction type
- GL distribution status
- service type code
- bill cycle code
- account ID
- service agreement ID

## Simple business summary
This table answers the question:

"For each financial transaction, what kind of transaction was it, what dollar amount did it carry, what account and service context did it belong to, and was it tied to a bill segment, adjustment, or payment?"

That makes it the clean finance header layer for Jasper Domains, Topics, ad hoc analysis, and simple speaking summaries.
