-- billing_completeness_reconciliation_jrs_derived.sql
-- Jasperserver Domain Derived Table safe: NO WITH clauses.
-- Use bind controls/filters from Jasper Domain layer or report input controls.
--
-- Bind variables:
--   :start_dt            DATE
--   :end_dt              DATE
--   :bill_cyc_cd         VARCHAR2 (nullable)
--   :active_sa_status    VARCHAR2 (nullable; commonly '20')
--   :exceptions_only     NUMBER   (0/1)

--------------------------------------------------------------------------------
-- 1) Cycle summary (expected vs generated)
--------------------------------------------------------------------------------
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
FROM (
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
        CASE WHEN G.BILL_ID IS NOT NULL THEN 1 ELSE 0 END AS GENERATED_BILL_SW,
        CASE WHEN BS.BSEG_ID IS NOT NULL THEN 1 ELSE 0 END AS GENERATED_BSEG_SW
    FROM (
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
    ) E
    LEFT JOIN (
        SELECT
            B.BILL_CYC_CD,
            B.ACCT_ID,
            B.BILL_ID,
            B.BILL_DT,
            B.BILL_STAT_FLG
        FROM CISADM.CI_BILL B
        WHERE B.BILL_DT >= :start_dt
          AND B.BILL_DT <  :end_dt + 1
          AND (:bill_cyc_cd IS NULL OR B.BILL_CYC_CD = :bill_cyc_cd)
    ) G
      ON G.ACCT_ID = E.ACCT_ID
     AND G.BILL_CYC_CD = E.BILL_CYC_CD
    LEFT JOIN (
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
    ) BS
      ON BS.BILL_ID = G.BILL_ID
     AND BS.SA_ID = E.SA_ID
) R
GROUP BY R.BILL_CYC_CD, TRUNC(R.BILL_DT)
HAVING (:exceptions_only = 0)
    OR COUNT(DISTINCT CASE WHEN R.GENERATED_BILL_SW = 0 THEN R.ACCT_ID END) > 0
ORDER BY BILL_DT DESC, R.BILL_CYC_CD;

--------------------------------------------------------------------------------
-- 2) Exception detail (account / SA / premise level)
--------------------------------------------------------------------------------
SELECT
    X.BILL_CYC_CD,
    X.BILL_DT,
    X.ACCT_ID,
    X.SA_ID,
    X.PREM_ID,
    X.BILL_ID,
    X.BILL_STAT_FLG,
    X.BSEG_ID,
    X.BSEG_STAT_FLG,
    CASE
      WHEN X.BILL_ID IS NULL THEN 'MISSING_BILL'
      WHEN X.BSEG_ID IS NULL THEN 'MISSING_BSEG'
      ELSE 'PRESENT'
    END AS RECON_RESULT
FROM (
    SELECT
        E.BILL_CYC_CD,
        G.BILL_DT,
        E.ACCT_ID,
        E.SA_ID,
        E.PREM_ID,
        G.BILL_ID,
        G.BILL_STAT_FLG,
        BS.BSEG_ID,
        BS.BSEG_STAT_FLG
    FROM (
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
    ) E
    LEFT JOIN (
        SELECT
            B.BILL_CYC_CD,
            B.ACCT_ID,
            B.BILL_ID,
            B.BILL_DT,
            B.BILL_STAT_FLG
        FROM CISADM.CI_BILL B
        WHERE B.BILL_DT >= :start_dt
          AND B.BILL_DT <  :end_dt + 1
          AND (:bill_cyc_cd IS NULL OR B.BILL_CYC_CD = :bill_cyc_cd)
    ) G
      ON G.ACCT_ID = E.ACCT_ID
     AND G.BILL_CYC_CD = E.BILL_CYC_CD
    LEFT JOIN (
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
    ) BS
      ON BS.BILL_ID = G.BILL_ID
     AND BS.SA_ID = E.SA_ID
) X
WHERE (:exceptions_only = 0)
   OR X.BILL_ID IS NULL
   OR X.BSEG_ID IS NULL
ORDER BY X.BILL_DT DESC NULLS LAST, X.BILL_CYC_CD, X.ACCT_ID, X.SA_ID;

--------------------------------------------------------------------------------
-- Suggested indexes (validate existing indexes first)
--------------------------------------------------------------------------------
-- CREATE INDEX IX_CI_BILL_DT_CYC_ACCT
--   ON CISADM.CI_BILL (BILL_DT, BILL_CYC_CD, ACCT_ID);
--
-- CREATE INDEX IX_CI_BSEG_CRE_CYC_BILL_SA
--   ON CISADM.CI_BSEG (CRE_DTTM, BILL_CYC_CD, BILL_ID, SA_ID);
--
-- CREATE INDEX IX_CI_SA_ACCT_STATUS
--   ON CISADM.CI_SA (ACCT_ID, SA_STATUS_FLG);
--
-- CREATE INDEX IX_CI_ACCT_CYC_ACCT
--   ON CISADM.CI_ACCT (BILL_CYC_CD, ACCT_ID);
