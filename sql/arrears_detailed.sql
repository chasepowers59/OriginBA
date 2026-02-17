-- GOVERNED: Detailed Running Arrear Balance (for Jaspersoft JDBC evidence table only)
-- Source: Working file.sql
-- Not run by the pipeline; use in Jaspersoft reports for row-level aging and running balance.
-- Value: How debt accumulates over time per service agreement (AGE, RUNNING_ARREAR_BAL)

SELECT
    FT.SA_ID,
    (TRUNC(SYSDATE) - FT.ARS_DT) AS AGE,
    FT.CUR_AMT AS TRANSACTION_AMT,
    SUM(FT.CUR_AMT) OVER (
        PARTITION BY FT.SA_ID
        ORDER BY (TRUNC(SYSDATE) - FT.ARS_DT)
        ROWS UNBOUNDED PRECEDING
    ) AS RUNNING_ARREAR_BAL
FROM CISADM.CI_FT FT
WHERE FT.FREEZE_SW = 'Y'
  AND FT.NOT_IN_ARS_SW = 'N'
  AND FT.FT_TYPE_FLG NOT IN ('PS', 'PX')
  AND NOT (FT.CUR_AMT < 0 AND FT.FT_TYPE_FLG IN ('AD','AX'))
ORDER BY FT.SA_ID, AGE ASC;
