# Finance FT GL Distribution Snapshot

## Purpose
`CISADM.FT_GL_DISTRIBUTION_RPT_CURR` is the finance snapshot for analyzing FT type breakdowns inside GL accounts.

It is designed for ad hoc reporting where users need GL account detail and also want to see the FT header context that produced each GL line.

## Grain
One row per `CI_FT_GL` line.

Natural key:
- `FT_ID`
- `GL_SEQ_NBR`

## Driving tables
- `CISADM.CI_FT_GL`
- `CISADM.CI_FT`

The snapshot intentionally repeats FT header attributes on each GL line. That is correct for this subject because the business question is about GL detail by FT type, not unduplicated FT-header totals.

If users need unduplicated FT-header totals, use the FT header snapshot `CISADM.FT_RPT_CURR` instead.

## What is included
- GL account, distribution code, GL amount, and statistic amount
- FT type, GL distribution status, accounting date, bill ID, SA ID, and core FT indicators
- SA and account classification fields for slicing the GL data
- customer trace fields (`PER_ID`, `CUSTOMER_NAME_UPR`) resolved to one account-person row
- FT-type-specific child detail for bill segments, adjustments, and pay segments
- balance control group status and balances

## What was intentionally removed
- full premise address and other customer-facing location detail from the legacy XML
- person-name joins that are not needed for FT-type-by-GL-account analysis
- the legacy XML's mixed-grain assumptions

## Key design rule
This snapshot uses `CI_FT_GL` grain. FT totals such as `CUR_AMT` and `TOT_AMT` repeat across multiple GL lines by design and should not be summed as if they were GL-line amounts.

For financial totals at this grain, users should aggregate:
- `GL_AMOUNT`
- `STATISTIC_AMOUNT`

`STATISTIC_AMOUNT` should be stored without a forced scale in `CISADM.FT_GL_DISTRIBUTION_RPT_CURR`. The source value can carry fractional precision beyond cents, so a fixed `NUMBER(15,2)` definition introduces rounding drift in exact reconciliations.

## Best use cases
- FT type breakdowns inside GL accounts
- distribution-code analysis by FT type
- GL detail reconciliation back to FT headers
- adjustment-to-GL trace reporting with account, SA, customer, and transfer-adjustment context
- finance ad hoc views by account class, SA type, or bill cycle

## Business summary
This table answers the question: "Which FT types are feeding each GL account and distribution code, and what GL amounts are associated with them?"

It gives finance users a single governed dataset for GL-line analysis without forcing them to reconstruct the FT, SA, account, and child-transaction joins at runtime.

## XML artifact
Importable Domain XML:
- `domains/exports/manual_imports/FT_GL_DISTRIBUTION_RPT_CURR_End_User_Friendly.xml`

Companion XML inventory:
- `sql/performance/snapshots/docs/snapshot_xml_inventory.md`

## SQL Developer runbook
For exact SQL Developer steps to inspect the table, view the current procedure, and validate the scheduler job, use:
- `sql/performance/snapshots/docs/snapshot_sqldeveloper_runbook.md` under `FT_GL_DISTRIBUTION_RPT_CURR`
