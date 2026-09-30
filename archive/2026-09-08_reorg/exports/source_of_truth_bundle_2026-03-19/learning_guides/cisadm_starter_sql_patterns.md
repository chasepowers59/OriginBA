# CISADM Starter SQL Patterns

## Purpose
These are starter SQL patterns for common CISADM reporting questions.

They are intentionally simple:
- read-only
- portable
- business-grain-first
- easy to adapt into report SQL

They are not meant to be final production queries without validation.

## Rules Before Use
1. State the row grain first.
2. Confirm what the query should exclude.
3. Add date filters early on the driving fact table.
4. Aggregate detail before joining broad dimensions.
5. Validate counts before and after optional joins.

## 1. Active Service Agreements By Account

### Grain
One row per account.

```sql
SELECT
    A.ACCT_ID,
    COUNT(DISTINCT SA.SA_ID) AS active_sa_count
FROM CISADM.CI_ACCT A
JOIN CISADM.CI_SA SA
  ON SA.ACCT_ID = A.ACCT_ID
 AND NULLIF(TRIM(SA.SA_STATUS_FLG), '') = '20'
GROUP BY A.ACCT_ID;
```

Includes:
- accounts with at least one active SA

Excludes:
- accounts with zero active SAs

## 2. Actual Billed Population

### Grain
One row per bill segment.

```sql
SELECT
    BSEG.BSEG_ID,
    BSEG.SA_ID,
    BSEG.BILL_ID,
    BSEG.BILL_CYC_CD,
    BSEG.START_DT,
    BSEG.END_DT,
    BSEG.BSEG_STAT_FLG
FROM CISADM.CI_BSEG BSEG;
```

Includes:
- only service agreements that created bill segments

Excludes:
- expected-but-unbilled service agreements

## 3. Expected vs Actual Billing Starter

### Grain
One row per active service agreement.

```sql
WITH active_sa AS (
    SELECT
        SA.SA_ID,
        SA.ACCT_ID
    FROM CISADM.CI_SA SA
    WHERE NULLIF(TRIM(SA.SA_STATUS_FLG), '') = '20'
),
billed_sa AS (
    SELECT DISTINCT
        BSEG.SA_ID
    FROM CISADM.CI_BSEG BSEG
)
SELECT
    A.SA_ID,
    A.ACCT_ID,
    CASE
      WHEN B.SA_ID IS NOT NULL THEN 'BILLED'
      ELSE 'NOT_BILLED'
    END AS billing_status
FROM active_sa A
LEFT JOIN billed_sa B
  ON B.SA_ID = A.SA_ID;
```

Includes:
- active SA population

Excludes:
- inactive or closed SA population

## 4. Account Debt Summary

### Grain
One row per account.

```sql
SELECT
    A.ACCT_ID,
    SUM(FT.CUR_AMT) AS total_balance_amt,
    SUM(CASE
          WHEN FT.NOT_IN_ARS_SW = 'N'
           AND FT.ARS_DT IS NOT NULL
          THEN FT.CUR_AMT
          ELSE 0
        END) AS arrears_amt
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
- frozen FT rows tied to active SAs

Excludes:
- non-frozen transactions
- inactive-SA-only balances

## 5. Debt Over 60 Days

### Grain
One row per account.

```sql
SELECT
    A.ACCT_ID,
    SUM(CASE
          WHEN FT.NOT_IN_ARS_SW = 'N'
           AND FT.ARS_DT IS NOT NULL
           AND (TRUNC(:end_ts) - FT.ARS_DT) > 60
          THEN FT.CUR_AMT
          ELSE 0
        END) AS debt_over_60
FROM CISADM.CI_ACCT A
JOIN CISADM.CI_SA SA
  ON SA.ACCT_ID = A.ACCT_ID
JOIN CISADM.CI_FT FT
  ON FT.SA_ID = SA.SA_ID
WHERE NULLIF(TRIM(SA.SA_STATUS_FLG), '') = '20'
  AND FT.FREEZE_SW = 'Y'
GROUP BY A.ACCT_ID;
```

## 6. Payment Arrangement Starter

### Grain
One row per payment arrangement request.

```sql
SELECT
    PA.PA_RQST_ID,
    PA.DOWN_PYMT_AMT,
    PA.INSTLMT_AMT,
    PA.NBR_OF_INST
FROM CISADM.C1_PA_RQST PA;
```

Includes:
- arrangement requests

Excludes:
- debt detail unless joined to related objects and FT/account context

## 7. Usage Transaction Summary

### Grain
One row per usage transaction.

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
    U.USG_EXT_ID,
    U.BO_STATUS_CD,
    U.START_DTTM,
    U.END_DTTM,
    Q.usage_qty
FROM CISADM.D1_USAGE U
LEFT JOIN usage_qty Q
  ON Q.D1_USAGE_ID = U.D1_USAGE_ID
WHERE U.BO_STATUS_CD = 'SENT';
```

Includes:
- `SENT` usage rows

Excludes:
- non-`SENT` usage rows
- account context unless bridged to `C1_USAGE` and `CI_SA`

## 8. Account to Usage Starter

### Grain
One row per usage transaction.

```sql
WITH usage_qty AS (
    SELECT
        UPSQ.D1_USAGE_ID,
        SUM(UPSQ.QUANTITY) AS usage_qty
    FROM CISADM.D1_USAGE_PERIOD_SQ UPSQ
    GROUP BY UPSQ.D1_USAGE_ID
)
SELECT
    A.ACCT_ID,
    SA.SA_ID,
    CU.USAGE_ID,
    U.D1_USAGE_ID,
    Q.usage_qty
FROM CISADM.CI_ACCT A
JOIN CISADM.CI_SA SA
  ON SA.ACCT_ID = A.ACCT_ID
JOIN CISADM.C1_USAGE CU
  ON CU.SA_ID = SA.SA_ID
JOIN CISADM.D1_USAGE U
  ON U.USG_EXT_ID = CU.USAGE_ID
LEFT JOIN usage_qty Q
  ON Q.D1_USAGE_ID = U.D1_USAGE_ID
WHERE NULLIF(TRIM(SA.SA_STATUS_FLG), '') = '20'
  AND CU.BO_STATUS_CD = 'BD-PROC'
  AND U.BO_STATUS_CD = 'SENT';
```

Includes:
- active-SA processed usage rows

Excludes:
- raw reads
- financial/billed amounts

## 9. Service Point to Device Starter

### Grain
One row per install event.

```sql
SELECT
    SP.SP_ID,
    IE.D1_INSTALL_EVT_ID,
    IE.D1_INSTALL_DTTM,
    CFG.D1_DVC_CFG_ID,
    DVC.D1_DEVICE_ID
FROM CISADM.CI_SP SP
JOIN CISADM.D1_INSTALL_EVT IE
  ON IE.D1_SP_ID = SP.SP_ID
JOIN CISADM.D1_DVC_CFG CFG
  ON CFG.D1_DVC_CFG_ID = IE.D1_DVC_CFG_ID
JOIN CISADM.D1_DVC DVC
  ON DVC.D1_DEVICE_ID = CFG.D1_DEVICE_ID;
```

Includes:
- service points with install events

Excludes:
- service points with no install history

## 10. Service Points Missing Install Event

### Grain
One row per service point.

```sql
SELECT
    SP.SP_ID
FROM CISADM.CI_SP SP
LEFT JOIN CISADM.D1_INSTALL_EVT IE
  ON IE.D1_SP_ID = SP.SP_ID
WHERE IE.D1_SP_ID IS NULL;
```

Includes:
- service points with no install-event linkage

Excludes:
- service points with at least one install event

## 11. Field Activity Aging Starter

### Grain
One row per field activity.

```sql
SELECT
    A.D1_ACTIVITY_ID,
    A.D1_SP,
    A.ACTIVITY_TYPE_CD,
    A.BO_STATUS_CD,
    A.CRE_DTTM,
    A.START_DTTM,
    A.END_DTTM
FROM CISADM.D1_ACTIVITY A;
```

Includes:
- all field activities

Excludes:
- service-point/customer enrichment unless added

## 12. Missing GL Status Starter

### Grain
One row per financial transaction.

```sql
SELECT
    FT.FT_ID,
    FT.SA_ID,
    FT.CRE_DTTM,
    FT.CUR_AMT,
    FT.GL_DISTRIB_STATUS
FROM CISADM.CI_FT FT
WHERE NULLIF(TRIM(FT.GL_DISTRIB_STATUS), '') IS NULL;
```

Includes:
- transactions with missing GL distribution status

Excludes:
- transactions with populated GL distribution status

## 13. Lookup Translation Pattern

### Grain
Same as the driving table.

```sql
LEFT JOIN CISADM.CI_LOOKUP_VAL_L LU
  ON TRIM(LU.FIELD_NAME) = 'BSEG_STAT_FLG'
 AND TRIM(LU.FIELD_VALUE) = TRIM(BSEG.BSEG_STAT_FLG)
 AND LU.LANGUAGE_CD IN ('ENG', 'EN')
```

Use this when:
- the code is hard to interpret without business labels

Risk:
- do not let a lookup join change row counts

## 14. Join Validation Pattern

### Grain
Same as the driving table.

```sql
WITH base AS (
    SELECT
        BSEG.BSEG_ID
    FROM CISADM.CI_BSEG BSEG
),
enriched AS (
    SELECT
        B.BSEG_ID
    FROM base B
    LEFT JOIN CISADM.CI_BSEG_EXCP E
      ON E.BSEG_ID = B.BSEG_ID
)
SELECT
    (SELECT COUNT(*) FROM base) AS base_cnt,
    (SELECT COUNT(*) FROM enriched) AS enriched_cnt
FROM dual;
```

Use this when:
- you want to confirm an enrichment join did not multiply the population

## 15. Questions To Answer Before Promoting A Query
1. What is the row grain?
2. What does the query intentionally exclude?
3. Which join is optional?
4. Which join can multiply rows?
5. Which fact table best matches the business question?
6. Did counts change after enrichment joins?

## Source Alignment
- `knowledge_base/oracle_c2m_query_patterns.md`
- `knowledge_base/c2m_cisadm/cisadm_core_model.md`
- `knowledge_base/c2m_cisadm/performance_playbook.md`
- `docs/sql_quality_workflow.md`
