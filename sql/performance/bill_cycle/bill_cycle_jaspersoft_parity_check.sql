-- bill_cycle_jaspersoft_parity_check.sql
-- Purpose: control totals + fingerprint to validate DB results vs Jasper output.
-- Set parameters once and use same values in Jasper input controls.
--
-- Parameters (replace literals as needed):
--   START_DATE      = DATE '2025-12-01'
--   END_DATE        = DATE '2025-12-31'
--   BILL_CYCLE_CODE = '01'      -- NULL for all
--   ERRORS_ONLY     = 0         -- drilldown only
--   MOST_RECENT_ONLY= 0

--------------------------------------------------------------------------------
-- A) SUMMARY parity check
--------------------------------------------------------------------------------
WITH params AS (
    SELECT
        DATE '2025-12-01' AS START_DATE,
        DATE '2025-12-31' AS END_DATE,
        '01' AS BILL_CYCLE_CODE,
        0 AS MOST_RECENT_ONLY
    FROM dual
),
active_sa AS (
    SELECT SA_ID, ACCT_ID
    FROM CISADM.CI_SA
    WHERE NULLIF(TRIM(SA_STATUS_FLG), '') = '20'
),
base_bseg AS (
    SELECT
        TRIM(S.BILL_CYC_CD) AS BILL_CYCLE_CODE,
        S.BILL_ID,
        S.SA_ID,
        TRUNC(S.CRE_DTTM) AS BSEG_CREATE_DATE
    FROM CISADM.CI_BSEG S
    CROSS JOIN params P
    WHERE TRIM(S.BILL_CYC_CD) IS NOT NULL
      AND S.CRE_DTTM >= P.START_DATE
      AND S.CRE_DTTM <  P.END_DATE + 1
      AND (NULLIF(TRIM(P.BILL_CYCLE_CODE), '') IS NULL OR TRIM(S.BILL_CYC_CD) = TRIM(P.BILL_CYCLE_CODE))
),
eligible_bseg AS (
    SELECT B.BILL_CYCLE_CODE, B.BILL_ID, B.SA_ID, B.BSEG_CREATE_DATE, A.ACCT_ID
    FROM base_bseg B
    JOIN active_sa A ON A.SA_ID = B.SA_ID
),
summary_rows AS (
    SELECT
        E.BILL_CYCLE_CODE,
        COUNT(*) AS BILL_SEGMENT_COUNT,
        COUNT(DISTINCT E.BILL_ID) AS BILL_COUNT,
        COUNT(DISTINCT E.SA_ID) AS ACTIVE_SERVICE_AGREEMENT_COUNT,
        COUNT(DISTINCT E.ACCT_ID) AS ACTIVE_ACCOUNT_COUNT,
        MIN(E.BSEG_CREATE_DATE) AS FIRST_BSEG_DATE,
        MAX(E.BSEG_CREATE_DATE) AS LAST_BSEG_DATE
    FROM eligible_bseg E
    GROUP BY E.BILL_CYCLE_CODE
),
summary_marked AS (
    SELECT
        S.*,
        CASE WHEN S.LAST_BSEG_DATE = MAX(S.LAST_BSEG_DATE) OVER () THEN 'Y' ELSE 'N' END AS MOST_RECENT_BILL_CYCLE_SW
    FROM summary_rows S
)
SELECT
    'SUMMARY' AS RESULT_SET,
    COUNT(*) AS ROW_CNT,
    SUM(BILL_SEGMENT_COUNT) AS BILL_SEGMENT_CNT,
    SUM(BILL_COUNT) AS BILL_CNT,
    SUM(ACTIVE_SERVICE_AGREEMENT_COUNT) AS ACTIVE_SA_CNT,
    SUM(ACTIVE_ACCOUNT_COUNT) AS ACTIVE_ACCT_CNT,
    SUM(
        ORA_HASH(
            NVL(BILL_CYCLE_CODE,'') || '|' ||
            TO_CHAR(BILL_SEGMENT_COUNT) || '|' ||
            TO_CHAR(BILL_COUNT) || '|' ||
            TO_CHAR(ACTIVE_SERVICE_AGREEMENT_COUNT) || '|' ||
            TO_CHAR(ACTIVE_ACCOUNT_COUNT) || '|' ||
            NVL(MOST_RECENT_BILL_CYCLE_SW,'')
        )
    ) AS ROW_FINGERPRINT
FROM summary_marked SM
CROSS JOIN params P
WHERE P.MOST_RECENT_ONLY = 0 OR SM.MOST_RECENT_BILL_CYCLE_SW = 'Y';

--------------------------------------------------------------------------------
-- B) DRILLDOWN parity check
--------------------------------------------------------------------------------
WITH params AS (
    SELECT
        DATE '2025-12-01' AS START_DATE,
        DATE '2025-12-31' AS END_DATE,
        '01' AS BILL_CYCLE_CODE,
        0 AS ERRORS_ONLY,
        0 AS MOST_RECENT_ONLY
    FROM dual
),
active_sa AS (
    SELECT SA_ID, ACCT_ID
    FROM CISADM.CI_SA
    WHERE NULLIF(TRIM(SA_STATUS_FLG), '') = '20'
),
base AS (
    SELECT
        TRIM(S.BILL_CYC_CD) AS BILL_CYCLE_CODE,
        S.BILL_ID,
        S.BSEG_ID,
        S.SA_ID,
        S.PREM_ID,
        S.BSEG_STAT_FLG,
        S.CRE_DTTM AS BSEG_CREATE_DTTM,
        A.ACCT_ID,
        B.BILL_DT,
        B.CRE_DTTM AS BILL_CREATE_DTTM,
        B.BILL_STAT_FLG
    FROM CISADM.CI_BSEG S
    JOIN active_sa A ON A.SA_ID = S.SA_ID
    LEFT JOIN CISADM.CI_BILL B ON B.BILL_ID = S.BILL_ID
    CROSS JOIN params P
    WHERE TRIM(S.BILL_CYC_CD) IS NOT NULL
      AND S.CRE_DTTM >= P.START_DATE
      AND S.CRE_DTTM <  P.END_DATE + 1
      AND (NULLIF(TRIM(P.BILL_CYCLE_CODE), '') IS NULL OR TRIM(S.BILL_CYC_CD) = TRIM(P.BILL_CYCLE_CODE))
),
bill_status AS (
    SELECT TRIM(FIELD_VALUE) AS STATUS_CODE, MAX(DESCR) AS STATUS_DESCRIPTION
    FROM CISADM.CI_LOOKUP_VAL_L
    WHERE TRIM(FIELD_NAME) = 'BILL_STAT_FLG' AND LANGUAGE_CD = 'ENG'
    GROUP BY TRIM(FIELD_VALUE)
),
bseg_status AS (
    SELECT TRIM(FIELD_VALUE) AS STATUS_CODE, MAX(DESCR) AS STATUS_DESCRIPTION
    FROM CISADM.CI_LOOKUP_VAL_L
    WHERE TRIM(FIELD_NAME) = 'BSEG_STAT_FLG' AND LANGUAGE_CD = 'ENG'
    GROUP BY TRIM(FIELD_VALUE)
),
cycle_last_dt AS (
    SELECT BILL_CYCLE_CODE, MAX(TRUNC(NVL(BILL_DT, BSEG_CREATE_DTTM))) AS CYCLE_LAST_EVENT_DATE
    FROM base
    GROUP BY BILL_CYCLE_CODE
),
drill_rows AS (
    SELECT
        B.BILL_CYCLE_CODE,
        B.ACCT_ID AS ACCOUNT_ID,
        B.SA_ID AS SERVICE_AGREEMENT_ID,
        B.BILL_ID,
        B.BSEG_ID AS BILL_SEGMENT_ID,
        CASE
            WHEN REGEXP_LIKE(UPPER(NVL(SS.STATUS_DESCRIPTION, '')), 'ERROR|EXCEPTION|FAIL|CANCEL')
              OR REGEXP_LIKE(UPPER(NVL(BS.STATUS_DESCRIPTION, '')), 'ERROR|EXCEPTION|FAIL|CANCEL')
            THEN 'Y' ELSE 'N'
        END AS IS_ERROR_SW,
        CASE
            WHEN CLD.CYCLE_LAST_EVENT_DATE = MAX(CLD.CYCLE_LAST_EVENT_DATE) OVER () THEN 'Y'
            ELSE 'N'
        END AS MOST_RECENT_BILL_CYCLE_SW
    FROM base B
    LEFT JOIN bill_status BS ON BS.STATUS_CODE = TRIM(B.BILL_STAT_FLG)
    LEFT JOIN bseg_status SS ON SS.STATUS_CODE = TRIM(B.BSEG_STAT_FLG)
    LEFT JOIN cycle_last_dt CLD ON CLD.BILL_CYCLE_CODE = B.BILL_CYCLE_CODE
)
SELECT
    'DRILLDOWN' AS RESULT_SET,
    COUNT(*) AS ROW_CNT,
    COUNT(DISTINCT BILL_ID) AS BILL_CNT,
    COUNT(DISTINCT BILL_SEGMENT_ID) AS BILL_SEGMENT_CNT,
    COUNT(DISTINCT SERVICE_AGREEMENT_ID) AS ACTIVE_SA_CNT,
    COUNT(DISTINCT ACCOUNT_ID) AS ACTIVE_ACCT_CNT,
    SUM(
        ORA_HASH(
            NVL(BILL_CYCLE_CODE,'') || '|' ||
            NVL(ACCOUNT_ID,'') || '|' ||
            NVL(SERVICE_AGREEMENT_ID,'') || '|' ||
            NVL(BILL_ID,'') || '|' ||
            NVL(BILL_SEGMENT_ID,'')
        )
    ) AS ROW_FINGERPRINT
FROM drill_rows D
CROSS JOIN params P
WHERE (P.ERRORS_ONLY = 0 OR D.IS_ERROR_SW = 'Y')
  AND (P.MOST_RECENT_ONLY = 0 OR D.MOST_RECENT_BILL_CYCLE_SW = 'Y');

