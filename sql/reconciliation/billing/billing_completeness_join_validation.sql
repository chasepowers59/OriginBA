-- billing_completeness_join_validation.sql
-- Purpose: validate join behavior and detect where expected rows disappear.
--
-- Bind variables:
--   :bill_cyc_cd      VARCHAR2 (nullable)
--   :from_dt          DATE     (nullable; for generated bill window)
--   :to_dt            DATE     (nullable)

--------------------------------------------------------------------------------
-- 1) Stage counts
--------------------------------------------------------------------------------
SELECT 'EXPECTED_BASE' AS STAGE, COUNT(*) AS ROW_CNT
FROM (
    SELECT A.BILL_CYC_CD, S.ACCT_ID, S.SA_ID, S.CHAR_PREM_ID AS PREM_ID
    FROM CISADM.CI_SA S
    JOIN CISADM.CI_ACCT A ON A.ACCT_ID = S.ACCT_ID
    WHERE S.SA_STATUS_FLG = '20'
      AND (:bill_cyc_cd IS NULL OR A.BILL_CYC_CD = :bill_cyc_cd)
)
UNION ALL
SELECT 'GENERATED_BILL', COUNT(*)
FROM CISADM.CI_BILL B
WHERE (:bill_cyc_cd IS NULL OR B.BILL_CYC_CD = :bill_cyc_cd)
  AND (:from_dt IS NULL OR B.BILL_DT >= :from_dt)
  AND (:to_dt   IS NULL OR B.BILL_DT <  :to_dt + 1)
UNION ALL
SELECT 'GENERATED_BSEG', COUNT(*)
FROM CISADM.CI_BSEG S
WHERE (:bill_cyc_cd IS NULL OR S.BILL_CYC_CD = :bill_cyc_cd)
  AND (:from_dt IS NULL OR S.CRE_DTTM >= :from_dt)
  AND (:to_dt   IS NULL OR S.CRE_DTTM <  :to_dt + 1);

--------------------------------------------------------------------------------
-- 2) Join health: expected -> bill
--------------------------------------------------------------------------------
SELECT
    COUNT(*) AS EXPECTED_ROWS,
    COUNT(CASE WHEN G.BILL_ID IS NOT NULL THEN 1 END) AS MATCHED_TO_BILL_ROWS,
    COUNT(CASE WHEN G.BILL_ID IS NULL THEN 1 END) AS MISSING_BILL_ROWS
FROM (
    SELECT A.BILL_CYC_CD, S.ACCT_ID, S.SA_ID, S.CHAR_PREM_ID AS PREM_ID
    FROM CISADM.CI_SA S
    JOIN CISADM.CI_ACCT A ON A.ACCT_ID = S.ACCT_ID
    WHERE S.SA_STATUS_FLG = '20'
      AND (:bill_cyc_cd IS NULL OR A.BILL_CYC_CD = :bill_cyc_cd)
) E
LEFT JOIN (
    SELECT B.BILL_CYC_CD, B.ACCT_ID, B.BILL_ID, B.BILL_DT, B.CRE_DTTM
    FROM CISADM.CI_BILL B
    WHERE (:bill_cyc_cd IS NULL OR B.BILL_CYC_CD = :bill_cyc_cd)
      AND (:from_dt IS NULL OR B.BILL_DT >= :from_dt)
      AND (:to_dt   IS NULL OR B.BILL_DT <  :to_dt + 1)
) G
  ON G.ACCT_ID = E.ACCT_ID
 AND G.BILL_CYC_CD = E.BILL_CYC_CD;

--------------------------------------------------------------------------------
-- 3) Join health: bill -> bseg by BILL_ID + SA_ID (current production key)
--------------------------------------------------------------------------------
SELECT
    COUNT(*) AS BILL_EXPECTED_ROWS,
    COUNT(CASE WHEN BS.BSEG_ID IS NOT NULL THEN 1 END) AS MATCHED_TO_BSEG_ROWS,
    COUNT(CASE WHEN BS.BSEG_ID IS NULL THEN 1 END) AS MISSING_BSEG_ROWS
FROM (
    SELECT E.BILL_CYC_CD, E.ACCT_ID, E.SA_ID, G.BILL_ID, G.BILL_DT
    FROM (
        SELECT A.BILL_CYC_CD, S.ACCT_ID, S.SA_ID
        FROM CISADM.CI_SA S
        JOIN CISADM.CI_ACCT A ON A.ACCT_ID = S.ACCT_ID
        WHERE S.SA_STATUS_FLG = '20'
          AND (:bill_cyc_cd IS NULL OR A.BILL_CYC_CD = :bill_cyc_cd)
    ) E
    LEFT JOIN (
        SELECT B.BILL_CYC_CD, B.ACCT_ID, B.BILL_ID, B.BILL_DT
        FROM CISADM.CI_BILL B
        WHERE (:bill_cyc_cd IS NULL OR B.BILL_CYC_CD = :bill_cyc_cd)
          AND (:from_dt IS NULL OR B.BILL_DT >= :from_dt)
          AND (:to_dt   IS NULL OR B.BILL_DT <  :to_dt + 1)
    ) G
      ON G.ACCT_ID = E.ACCT_ID
     AND G.BILL_CYC_CD = E.BILL_CYC_CD
) J
LEFT JOIN CISADM.CI_BSEG BS
  ON BS.BILL_ID = J.BILL_ID
 AND BS.SA_ID = J.SA_ID;

--------------------------------------------------------------------------------
-- 4) Compare alternate bseg match rule (BILL_ID only) to diagnose SA key gaps
--------------------------------------------------------------------------------
SELECT
    'BILL_ID_PLUS_SA_ID' AS MATCH_RULE,
    COUNT(CASE WHEN BS.BSEG_ID IS NOT NULL THEN 1 END) AS MATCHED_ROWS
FROM (
    SELECT E.BILL_CYC_CD, E.ACCT_ID, E.SA_ID, G.BILL_ID
    FROM (
        SELECT A.BILL_CYC_CD, S.ACCT_ID, S.SA_ID
        FROM CISADM.CI_SA S
        JOIN CISADM.CI_ACCT A ON A.ACCT_ID = S.ACCT_ID
        WHERE S.SA_STATUS_FLG = '20'
          AND (:bill_cyc_cd IS NULL OR A.BILL_CYC_CD = :bill_cyc_cd)
    ) E
    LEFT JOIN (
        SELECT B.BILL_CYC_CD, B.ACCT_ID, B.BILL_ID, B.BILL_DT
        FROM CISADM.CI_BILL B
        WHERE (:bill_cyc_cd IS NULL OR B.BILL_CYC_CD = :bill_cyc_cd)
          AND (:from_dt IS NULL OR B.BILL_DT >= :from_dt)
          AND (:to_dt   IS NULL OR B.BILL_DT <  :to_dt + 1)
    ) G
      ON G.ACCT_ID = E.ACCT_ID
     AND G.BILL_CYC_CD = E.BILL_CYC_CD
) J
LEFT JOIN CISADM.CI_BSEG BS
  ON BS.BILL_ID = J.BILL_ID
 AND BS.SA_ID = J.SA_ID
UNION ALL
SELECT
    'BILL_ID_ONLY' AS MATCH_RULE,
    COUNT(CASE WHEN BS.BSEG_ID IS NOT NULL THEN 1 END) AS MATCHED_ROWS
FROM (
    SELECT E.BILL_CYC_CD, E.ACCT_ID, E.SA_ID, G.BILL_ID
    FROM (
        SELECT A.BILL_CYC_CD, S.ACCT_ID, S.SA_ID
        FROM CISADM.CI_SA S
        JOIN CISADM.CI_ACCT A ON A.ACCT_ID = S.ACCT_ID
        WHERE S.SA_STATUS_FLG = '20'
          AND (:bill_cyc_cd IS NULL OR A.BILL_CYC_CD = :bill_cyc_cd)
    ) E
    LEFT JOIN (
        SELECT B.BILL_CYC_CD, B.ACCT_ID, B.BILL_ID, B.BILL_DT
        FROM CISADM.CI_BILL B
        WHERE (:bill_cyc_cd IS NULL OR B.BILL_CYC_CD = :bill_cyc_cd)
          AND (:from_dt IS NULL OR B.BILL_DT >= :from_dt)
          AND (:to_dt   IS NULL OR B.BILL_DT <  :to_dt + 1)
    ) G
      ON G.ACCT_ID = E.ACCT_ID
     AND G.BILL_CYC_CD = E.BILL_CYC_CD
) J
LEFT JOIN CISADM.CI_BSEG BS
  ON BS.BILL_ID = J.BILL_ID;

