# Oracle C2M Query Patterns

## Status and Active Filters
- Active SA:
```sql
NULLIF(TRIM(SA.SA_STATUS_FLG), '') = '20'
```

## Safe Date Event Pattern
- Standard event date for billing event analytics:
```sql
TRUNC(NVL(B.BILL_DT, S.CRE_DTTM))
```

## Latest Event Per Cycle Pattern
```sql
MAX(TRUNC(NVL(B.BILL_DT, S.CRE_DTTM))) OVER (PARTITION BY TRIM(S.BILL_CYC_CD)) AS CYCLE_LAST_EVENT_DATE
```
Then filter:
```sql
WHERE EVENT_DATE = CYCLE_LAST_EVENT_DATE
```

## Bill Cycle Source Priority
1. `CI_BSEG.BILL_CYC_CD` for actual billed activity.
2. `CI_ACCT.BILL_CYC_CD` for expected cycle assignment.

## Description Lookup Pattern
```sql
LEFT JOIN (
  SELECT TRIM(BILL_CYC_CD) AS BILL_CYCLE_CODE, MAX(DESCR) AS BILL_CYCLE_DESCRIPTION
  FROM CISADM.CI_BILL_CYC_L
  WHERE LANGUAGE_CD IN ('ENG', 'EN')
  GROUP BY TRIM(BILL_CYC_CD)
) L
ON L.BILL_CYCLE_CODE = TRIM(S.BILL_CYC_CD)
```

## Status Description Pattern
```sql
LEFT JOIN (
  SELECT TRIM(FIELD_VALUE) AS STATUS_CODE, MAX(DESCR) AS STATUS_DESCRIPTION
  FROM CISADM.CI_LOOKUP_VAL_L
  WHERE TRIM(FIELD_NAME) = 'BSEG_STAT_FLG'
    AND LANGUAGE_CD = 'ENG'
  GROUP BY TRIM(FIELD_VALUE)
) SS
ON SS.STATUS_CODE = TRIM(S.BSEG_STAT_FLG)
```

## Error Detection Fallback
When no dedicated exception table is available:
```sql
REGEXP_LIKE(UPPER(NVL(STATUS_DESCRIPTION, '')), 'ERROR|EXCEPTION|FAIL|CANCEL')
```

## Avoid
- Hardcoding cycle lists across environments.
- Using `SYSDATE` windows without checking data freshness.
- Comparing expected all-active population against one-day actuals without context.
