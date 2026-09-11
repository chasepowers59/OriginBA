# CISADM SQL Cheat Sheet

## Purpose
This cheat sheet is for understanding Oracle C2M/CISADM dataflow, what a query slice does or does not include, and the rules to follow when building reporting SQL.

It is written for reporting and analysis work in this repository, not for transactional system development.

## Core Dataflow

### Billing and finance flow
```text
CI_ACCT
  -> CI_SA
    -> CI_BSEG
      -> CI_BILL
    -> CI_FT
      -> CI_FT_GL
```

### Usage and meter flow
```text
CI_ACCT
  -> CI_SA
    -> C1_USAGE
      -> D1_USAGE
        -> D1_USAGE_PERIOD_SQ

CI_SP
  -> D1_INSTALL_EVT
    -> D1_DVC_CFG
      -> D1_DVC
      -> D1_MEASR_COMP
```

### Field operations flow
```text
CI_SP
  -> D1_ACTIVITY
    -> D1_ACTIVITY_REL
    -> D1_ACTIVITY_REL_OBJ
```

## Fast Mental Model
- `CI_ACCT` is the customer financial umbrella.
- `CI_SA` is the service-level contract under the account.
- `CI_SP` is the physical delivery point.
- `CI_BSEG` is usually the best billing-period fact grain.
- `CI_BILL` is the final customer-facing bill header.
- `CI_FT` is usually the best accounting-impact fact grain.
- `D1_USAGE` is usually the best detailed usage transaction grain.
- `D1_INSTALL_EVT` connects device configuration to service point over time.

## What A Query Usually Includes

### If you start from `CI_ACCT`
Usually includes:
- account-level population
- all related service agreements if you join them
- customer finance rollups if you continue to `CI_FT`

Usually does not include:
- only active services, unless you filter for them
- only billed population, unless you join billing facts
- premise or device context, unless you explicitly join it

### If you start from `CI_SA`
Usually includes:
- service-level population
- cleaner alignment to billing and financial facts than account-only queries

Usually does not include:
- every account row, because some accounts may have multiple SAs
- premise/device details without more joins

### If you start from `CI_BSEG`
Usually includes:
- billed service periods
- bill-segment status and billing-period detail
- only entities that reached bill-segment creation

Usually does not include:
- customers expected to bill but not yet billed
- payments or full accounting context unless joined to `CI_FT`

### If you start from `CI_FT`
Usually includes:
- posted or in-flight financial impact rows
- arrears, charge, credit, payment-effect, or adjustment context

Usually does not include:
- one-row-per-bill logic
- usage quantities unless bridged carefully

### If you start from `D1_USAGE`
Usually includes:
- processed usage transaction rows
- usage status, usage timing, and usage exceptions

Usually does not include:
- raw inbound reads unless joined to IMD or measurement sources
- full billed dollars unless bridged to billing/financial facts

### If you start from `D1_INSTALL_EVT`
Usually includes:
- device-to-service-point history
- install/removal timing
- operational meter context

Usually does not include:
- customer balance context
- billed usage context without more joins

## What Common Filters Mean

### Active SA
```sql
NULLIF(TRIM(SA.SA_STATUS_FLG), '') = '20'
```
This usually means:
- you are limiting to active service agreements

This usually excludes:
- pending SAs
- stopped or closed SAs
- historical inactive agreements

### Processed usage
```sql
C1_USAGE.BO_STATUS_CD = 'BD-PROC'
AND D1_USAGE.BO_STATUS_CD = 'SENT'
```
This usually means:
- usage made it through the expected processing state

This usually excludes:
- unprocessed usage
- exception-state usage
- draft or intermediate lifecycle rows

### Frozen financial transactions
```sql
FT.FREEZE_SW = 'Y'
```
This usually means:
- the transaction is posted/finalized enough for finance-style reporting

This usually excludes:
- non-frozen or still-changing transactions

### Arrears-eligible debt
```sql
FT.NOT_IN_ARS_SW = 'N'
AND FT.ARS_DT IS NOT NULL
```
This usually means:
- the transaction can participate in arrears/debt aging logic

This usually excludes:
- rows intentionally kept out of arrears

## Inclusion and Exclusion Rules By Join Choice

### `INNER JOIN`
Use when:
- the joined record must exist for the business meaning to be valid

Effect:
- drops rows from the driving table when the child/enrichment row is missing

Typical good use:
- `CI_SA` to `CI_ACCT` when service agreements without accounts are invalid

Typical risk:
- joining optional lookup or optional enrichment tables and accidentally shrinking the population

### `LEFT JOIN`
Use when:
- missing child/enrichment data is still meaningful
- you want to preserve the driving population

Effect:
- keeps the row from the driving table even if enrichment is missing

Typical good use:
- lookups, optional contacts, optional alerts, optional device or financial enrichments

## Grain Rules

### Rule 1: Decide the row grain first
Ask:
- one row per account?
- one row per service agreement?
- one row per bill segment?
- one row per financial transaction?
- one row per usage transaction?

If you cannot answer that clearly, the query is not ready.

### Rule 2: Do not mix grains casually
Bad pattern:
- join `CI_BSEG` directly to multiple detail tables and assume totals still mean the same thing

Risk:
- duplicate amounts
- inflated counts
- inconsistent row counts between reports

### Rule 3: Pre-aggregate before broad enrichment
For usage:
- aggregate `D1_USAGE_PERIOD_SQ` or scalar detail before joining many dimensions

For finance:
- aggregate `CI_FT` before joining broad reference tables if the output is account-level or bill-level

## Safe Query Skeletons

### 1. Account -> SA -> FT debt summary
```sql
SELECT
    A.ACCT_ID,
    SUM(FT.CUR_AMT) AS total_amt
FROM CISADM.CI_ACCT A
JOIN CISADM.CI_SA SA
  ON SA.ACCT_ID = A.ACCT_ID
 AND NULLIF(TRIM(SA.SA_STATUS_FLG), '') = '20'
JOIN CISADM.CI_FT FT
  ON FT.SA_ID = SA.SA_ID
 AND FT.FREEZE_SW = 'Y'
GROUP BY A.ACCT_ID;
```
Includes:
- active-SA financial rows

Excludes:
- inactive-SA balances
- accounts with no active SA

### 2. SA -> BSEG billing population
```sql
SELECT
    S.SA_ID,
    BSEG.BSEG_ID,
    BSEG.BILL_ID
FROM CISADM.CI_SA S
JOIN CISADM.CI_BSEG BSEG
  ON BSEG.SA_ID = S.SA_ID;
```
Includes:
- only service agreements that produced bill segments

Excludes:
- expected-but-unbilled SAs

### 3. Usage transaction summary
```sql
WITH usage_qty AS (
    SELECT
        UPSQ.D1_USAGE_ID,
        SUM(UPSQ.QUANTITY) AS usage_qty
    FROM CISADM.D1_USAGE_PERIOD_SQ UPSQ
    GROUP BY UPSQ.D1_USAGE_ID
)
SELECT
    U.D1_USAGE_ID,
    Q.usage_qty
FROM CISADM.D1_USAGE U
LEFT JOIN usage_qty Q
  ON Q.D1_USAGE_ID = U.D1_USAGE_ID
WHERE U.BO_STATUS_CD = 'SENT';
```
Includes:
- all `SENT` usage rows
- usage quantity where available

Excludes:
- non-`SENT` usage rows

## Rules For Building Reporting SQL

### Business rules
1. Preserve the intended business population before optimizing.
2. Use the correct driving fact for the question.
3. Expected population and actual population are not the same thing.
4. A missing optional enrichment row should not silently remove the business row.

### Technical rules
1. Filter high-volume fact tables early.
2. Aggregate detail before joining wide dimensions.
3. Prefer bind variables and portable patterns.
4. Use read-only `SELECT` logic only in this repo's validation/reporting workflows.
5. Use language-safe lookup joins where applicable.

### Repository rules
1. Use source-of-truth mappings from `output/workstream_reporting_dictionary.json`.
2. Use read-only guards and validation workflow before DB execution.
3. Never assume a join is safe just because a foreign key name looks obvious.
4. For Domain work, avoid raw-table fan-out; establish grain first if needed.

## Red Flags
- counts rise sharply after adding an enrichment table
- totals change after joining lookups
- you cannot explain the row grain in one sentence
- you join usage detail and billing detail without aggregation
- you compare active population to billed population without clearly naming the difference
- you rely on code values without lookup translation

## Good Questions To Ask Before Writing SQL
1. What is the business population?
2. What should one row represent?
3. What records are intentionally excluded?
4. What status values define "complete" or "active"?
5. Which joins are optional enrichment versus required business relationships?
6. What could duplicate this row?

## Study Path
1. Learn `CI_ACCT`, `CI_SA`, `CI_SP`.
2. Learn `CI_BSEG`, `CI_BILL`, `CI_FT`.
3. Learn `C1_USAGE`, `D1_USAGE`, `D1_USAGE_PERIOD_SQ`.
4. Learn `D1_INSTALL_EVT`, `D1_DVC_CFG`, `D1_DVC`.
5. Learn lookup and support tables only after the fact grains make sense.

## Source Alignment
- `knowledge_base/oracle_c2m_query_patterns.md`
- `knowledge_base/c2m_cisadm/cisadm_core_model.md`
- `knowledge_base/c2m_cisadm/performance_playbook.md`
- `docs/sql_quality_workflow.md`
- `output/workstream_reporting_dictionary.json`
