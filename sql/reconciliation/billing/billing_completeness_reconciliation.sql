-- billing_completeness_reconciliation.sql
-- Purpose: Expected vs Generated billing reconciliation by cycle/date with exception rows.
-- Oracle 19/21c, bind-variable ready for Jasper/JRS.
--
-- Bind variables:
--   :start_dt              DATE
--   :end_dt                DATE
--   :bill_cyc_cd           VARCHAR2  (nullable)
--   :active_sa_status      VARCHAR2  (default typically '20' in many C2M implementations)
--   :exceptions_only       NUMBER    (0/1)
--
-- Notes:
-- - Tune active SA status code per client configuration.
-- - This query is designed as a domain/view seed, then exposed in Jasper as summary + detail reports.

EXPLAIN PLAN FOR
WITH expected_base AS (
    SELECT
        A.BILL_CYC_CD,
        S.ACCT_ID,
        S.SA_ID,
        S.CHAR_PREM_ID AS PREM_ID
    FROM CISADM.CI_SA S
    JOIN CISADM.CI_ACCT A
      ON A.ACCT_ID = S.ACCT_ID
    WHERE (:bill_cyc_cd IS NULL OR A.BILL_CYC_CD = :bill_cyc_cd)
      AND (:active_sa_status IS NULL OR S.SA_STATUS_FLG = :active_sa_status)
),
generated_bill AS (
    SELECT
        B.BILL_CYC_CD,
        B.ACCT_ID,
        B.BILL_ID,
        B.BILL_DT,
        B.BILL_STAT_FLG,
        B.CRE_DTTM,
        B.COMPLETE_DTTM
    FROM CISADM.CI_BILL B
    WHERE B.BILL_DT >= :start_dt
      AND B.BILL_DT <  :end_dt + 1
      AND (:bill_cyc_cd IS NULL OR B.BILL_CYC_CD = :bill_cyc_cd)
),
generated_bseg AS (
    SELECT
        S.BILL_ID,
        S.BILL_CYC_CD,
        S.SA_ID,
        S.PREM_ID,
        S.BSEG_ID,
        S.BSEG_STAT_FLG,
        S.CRE_DTTM AS BSEG_CRE_DTTM
    FROM CISADM.CI_BSEG S
    WHERE S.CRE_DTTM >= :start_dt
      AND S.CRE_DTTM <  :end_dt + 1
      AND (:bill_cyc_cd IS NULL OR S.BILL_CYC_CD = :bill_cyc_cd)
),
recon AS (
    SELECT
        E.BILL_CYC_CD,
        G.BILL_DT,
        E.ACCT_ID,
        E.SA_ID,
        E.PREM_ID,
        G.BILL_ID,
        G.BILL_STAT_FLG,
        G.CRE_DTTM       AS BILL_CRE_DTTM,
        G.COMPLETE_DTTM  AS BILL_COMPLETE_DTTM,
        BS.BSEG_ID,
        BS.BSEG_STAT_FLG,
        CASE WHEN G.BILL_ID IS NOT NULL THEN 1 ELSE 0 END AS GENERATED_BILL_SW,
        CASE WHEN BS.BSEG_ID IS NOT NULL THEN 1 ELSE 0 END AS GENERATED_BSEG_SW
    FROM expected_base E
    LEFT JOIN generated_bill G
      ON G.ACCT_ID = E.ACCT_ID
     AND G.BILL_CYC_CD = E.BILL_CYC_CD
    LEFT JOIN generated_bseg BS
      ON BS.BILL_ID = G.BILL_ID
     AND BS.SA_ID = E.SA_ID
)
SELECT
    R.BILL_CYC_CD,
    TRUNC(R.BILL_DT) AS BILL_DT,
    COUNT(DISTINCT R.ACCT_ID) AS EXPECTED_ACCT_CNT,
    COUNT(DISTINCT CASE WHEN R.GENERATED_BILL_SW = 1 THEN R.ACCT_ID END) AS GENERATED_BILL_ACCT_CNT,
    COUNT(DISTINCT CASE WHEN R.GENERATED_BSEG_SW = 1 THEN R.SA_ID END) AS GENERATED_BSEG_SA_CNT,
    COUNT(DISTINCT CASE WHEN R.GENERATED_BILL_SW = 0 THEN R.ACCT_ID END) AS MISSING_ACCT_CNT,
    ROUND(
      100
      * COUNT(DISTINCT CASE WHEN R.GENERATED_BILL_SW = 1 THEN R.ACCT_ID END)
      / NULLIF(COUNT(DISTINCT R.ACCT_ID), 0), 2
    ) AS BILL_COMPLETION_PCT
FROM recon R
GROUP BY R.BILL_CYC_CD, TRUNC(R.BILL_DT)
HAVING (:exceptions_only = 0)
    OR COUNT(DISTINCT CASE WHEN R.GENERATED_BILL_SW = 0 THEN R.ACCT_ID END) > 0
ORDER BY BILL_DT DESC, R.BILL_CYC_CD;

SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY(NULL,NULL,'ALL'));

--------------------------------------------------------------------------------
-- Exception detail query (premise/account/service agreement level)
--------------------------------------------------------------------------------
EXPLAIN PLAN FOR
WITH expected_base AS (
    SELECT
        A.BILL_CYC_CD,
        S.ACCT_ID,
        S.SA_ID,
        S.CHAR_PREM_ID AS PREM_ID
    FROM CISADM.CI_SA S
    JOIN CISADM.CI_ACCT A
      ON A.ACCT_ID = S.ACCT_ID
    WHERE (:bill_cyc_cd IS NULL OR A.BILL_CYC_CD = :bill_cyc_cd)
      AND (:active_sa_status IS NULL OR S.SA_STATUS_FLG = :active_sa_status)
),
generated_bill AS (
    SELECT
        B.BILL_CYC_CD,
        B.ACCT_ID,
        B.BILL_ID,
        B.BILL_DT,
        B.BILL_STAT_FLG,
        B.CRE_DTTM,
        B.COMPLETE_DTTM
    FROM CISADM.CI_BILL B
    WHERE B.BILL_DT >= :start_dt
      AND B.BILL_DT <  :end_dt + 1
      AND (:bill_cyc_cd IS NULL OR B.BILL_CYC_CD = :bill_cyc_cd)
),
generated_bseg AS (
    SELECT
        S.BILL_ID,
        S.BILL_CYC_CD,
        S.SA_ID,
        S.PREM_ID,
        S.BSEG_ID,
        S.BSEG_STAT_FLG
    FROM CISADM.CI_BSEG S
    WHERE S.CRE_DTTM >= :start_dt
      AND S.CRE_DTTM <  :end_dt + 1
      AND (:bill_cyc_cd IS NULL OR S.BILL_CYC_CD = :bill_cyc_cd)
)
SELECT
    E.BILL_CYC_CD,
    G.BILL_DT,
    E.ACCT_ID,
    E.SA_ID,
    E.PREM_ID,
    G.BILL_ID,
    G.BILL_STAT_FLG,
    BS.BSEG_ID,
    BS.BSEG_STAT_FLG,
    CASE
      WHEN G.BILL_ID IS NULL THEN 'MISSING_BILL'
      WHEN BS.BSEG_ID IS NULL THEN 'MISSING_BSEG'
      ELSE 'PRESENT'
    END AS RECON_RESULT
FROM expected_base E
LEFT JOIN generated_bill G
  ON G.ACCT_ID = E.ACCT_ID
 AND G.BILL_CYC_CD = E.BILL_CYC_CD
LEFT JOIN generated_bseg BS
  ON BS.BILL_ID = G.BILL_ID
 AND BS.SA_ID = E.SA_ID
WHERE (:exceptions_only = 0)
   OR G.BILL_ID IS NULL
   OR BS.BSEG_ID IS NULL
ORDER BY G.BILL_DT DESC NULLS LAST, E.BILL_CYC_CD, E.ACCT_ID, E.SA_ID;

SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY(NULL,NULL,'ALL'));

--------------------------------------------------------------------------------
-- Index recommendations (adjust to existing indexes before creating)
--------------------------------------------------------------------------------
-- 1) CI_BILL: BILL_DT + BILL_CYC_CD + ACCT_ID
-- CREATE INDEX IX_CI_BILL_DT_CYC_ACCT
--   ON CISADM.CI_BILL (BILL_DT, BILL_CYC_CD, ACCT_ID);
--
-- 2) CI_BSEG: CRE_DTTM + BILL_CYC_CD + BILL_ID + SA_ID
-- CREATE INDEX IX_CI_BSEG_CRE_CYC_BILL_SA
--   ON CISADM.CI_BSEG (CRE_DTTM, BILL_CYC_CD, BILL_ID, SA_ID);
--
-- 3) CI_SA: ACCT_ID + SA_STATUS_FLG
-- CREATE INDEX IX_CI_SA_ACCT_STATUS
--   ON CISADM.CI_SA (ACCT_ID, SA_STATUS_FLG);
--
-- 4) CI_ACCT: BILL_CYC_CD + ACCT_ID
-- CREATE INDEX IX_CI_ACCT_CYC_ACCT
--   ON CISADM.CI_ACCT (BILL_CYC_CD, ACCT_ID);
