-- Purpose:
--   Billed revenue with tax/non-tax split at BILL_ID + BSEG_ID grain.
--
-- Parameters (Oracle bind style):
--   :P_START_DATE           DATE   -- inclusive
--   :P_END_DATE             DATE   -- inclusive (query uses < end_date + 1)
--   :P_BILL_STAT_FLG        CHAR   -- default 'C' when null
--   :P_INCLUDE_NON_TAX      CHAR   -- 'Y' includes all rows, otherwise only rows with TAX_AMOUNT <> 0
--   :P_USE_SQI_TAX_RULE     CHAR   -- 'Y' enables fallback SQI tax classification
--
-- Notes:
--   1) RC_TYPE_FLG comes from CI_RC (not CI_BSEG_CALC directly).
--   2) Primary tax rule is RC_TYPE_FLG = 'TX'.
--   3) Optional fallback tax rule uses SQI_CD IN ('TAX','TX') when :P_USE_SQI_TAX_RULE = 'Y'.

WITH BASE_CALC AS (
  SELECT
    B.BILL_ID,
    S.BSEG_ID,
    B.BILL_DT,
    LN.CALC_AMT,
    LN.SQI_CD,
    RC.RC_TYPE_FLG
  FROM CISADM.CI_BILL B
  JOIN CISADM.CI_BSEG S
    ON S.BILL_ID = B.BILL_ID
  JOIN CISADM.CI_BSEG_CALC C
    ON C.BSEG_ID = S.BSEG_ID
  JOIN CISADM.CI_BSEG_CALC_LN LN
    ON LN.BSEG_ID = C.BSEG_ID
   AND LN.HEADER_SEQ = C.HEADER_SEQ
  LEFT JOIN CISADM.CI_RC RC
    ON RC.RS_CD = C.RS_CD
   AND RC.EFFDT = C.EFFDT
   AND RC.RC_SEQ = LN.RC_SEQ
  WHERE B.BILL_DT >= :P_START_DATE
    AND B.BILL_DT <  :P_END_DATE + 1
    AND B.BILL_STAT_FLG = NVL(:P_BILL_STAT_FLG, 'C')
),
AGG AS (
  SELECT
    X.BILL_ID,
    X.BSEG_ID,
    MAX(X.BILL_DT) AS BILL_DATE,
    SUM(NVL(X.CALC_AMT, 0)) AS TOTAL_CHARGES,
    SUM(
      CASE
        WHEN X.RC_TYPE_FLG = 'TX' THEN NVL(X.CALC_AMT, 0)
        WHEN :P_USE_SQI_TAX_RULE = 'Y' AND X.SQI_CD IN ('TAX', 'TX') THEN NVL(X.CALC_AMT, 0)
        ELSE 0
      END
    ) AS TAX_AMOUNT
  FROM BASE_CALC X
  GROUP BY
    X.BILL_ID,
    X.BSEG_ID
)
SELECT
  A.BILL_ID,
  A.BSEG_ID,
  A.BILL_DATE,
  A.TOTAL_CHARGES,
  A.TAX_AMOUNT,
  A.TOTAL_CHARGES - A.TAX_AMOUNT AS NON_TAX_AMOUNT,
  CASE
    WHEN A.TOTAL_CHARGES = 0 THEN 0
    ELSE ROUND((A.TAX_AMOUNT / A.TOTAL_CHARGES) * 100, 4)
  END AS TAX_PCT
FROM AGG A
WHERE :P_INCLUDE_NON_TAX = 'Y'
   OR A.TAX_AMOUNT <> 0
ORDER BY
  A.BILL_ID,
  A.BSEG_ID
