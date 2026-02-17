-- GOVERNED: Duplicate Payment Detection (exception reporting)
-- Source: S_C2M_TwoPayments_Same_Amount_2days_apart.sql
-- Used by: pipeline/fetch_usage.py (_QUERY_DUPLICATE_PAYMENT); also for Jaspersoft JDBC evidence table
-- Value: Flags potential double-billing (same amount today and yesterday)

SELECT b.ACCT_NBR,
       b.ACCT_PAYMENTS_TODAY,
       b.ACCT_PAYMENTS_YESTERDAY,
       'Potential Duplicate Payment' AS ANOMALY_TYPE
FROM (
    SELECT a.ACCT_ID AS ACCT_NBR,
            (SELECT NVL(SUM(ft2.CUR_AMT),0)
             FROM CISADM.CI_FT ft2
             JOIN CISADM.CI_SA sa2 ON sa2.SA_ID = ft2.SA_ID
                AND NULLIF(TRIM(sa2.SA_STATUS_FLG), '') = '20'
             WHERE sa2.ACCT_ID = a.ACCT_ID
                   AND ft2.REDUNDANT_SW = 'N'
                   AND ft2.FREEZE_SW = 'Y'
                   AND ft2.FT_TYPE_FLG IN ('PS', 'PX')
                   AND TRUNC(ft2.CRE_DTTM) = TRUNC(SYSDATE)
            ) AS ACCT_PAYMENTS_TODAY,
            (SELECT NVL(SUM(ft2.CUR_AMT),0)
             FROM CISADM.CI_FT ft2
             JOIN CISADM.CI_SA sa2 ON sa2.SA_ID = ft2.SA_ID
                AND NULLIF(TRIM(sa2.SA_STATUS_FLG), '') = '20'
             WHERE sa2.ACCT_ID = a.ACCT_ID
                   AND ft2.REDUNDANT_SW = 'N'
                   AND ft2.FREEZE_SW = 'Y'
                   AND ft2.FT_TYPE_FLG IN ('PS', 'PX')
                   AND TRUNC(ft2.CRE_DTTM) = TRUNC(SYSDATE) - 1
            ) AS ACCT_PAYMENTS_YESTERDAY
    FROM CISADM.CI_ACCT a
) b
WHERE b.ACCT_PAYMENTS_TODAY = b.ACCT_PAYMENTS_YESTERDAY
  AND b.ACCT_PAYMENTS_TODAY <> 0;
