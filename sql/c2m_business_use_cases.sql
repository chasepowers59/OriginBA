-- GOVERNED: C2M Utility Business Processes and Use Cases (Jaspersoft-ready)
-- Source of truth alignment:
--   - output/workstream_reporting_dictionary.json
--   - Domain Designs.xlsx
-- Rules:
--   - Read-only SELECT patterns.
--   - Bind-variable driven for report portability.
--   - No hardcoded client/account credentials.

--------------------------------------------------------------------------------
-- Required bind variables for these templates
--   :client_id      VARCHAR2
--   :start_ts       TIMESTAMP
--   :end_ts         TIMESTAMP
--   :acct_id        VARCHAR2 (optional for account-level runs)
--------------------------------------------------------------------------------

--------------------------------------------------------------------------------
-- Use Case 1: At-Risk Accounts for Collection Campaign
-- Business value:
--   Prioritize outreach where overdue debt and active alerts indicate near-term
--   collections risk.
--------------------------------------------------------------------------------
SELECT
    A.ACCT_ID,
    NULLIF(TRIM(A.COLL_CL_CD), '') AS COLL_CL_CD,
    SUM(CASE WHEN (TRUNC(:end_ts) - FT.ARS_DT) > 60 THEN FT.CUR_AMT ELSE 0 END) AS DEBT_OVER_60,
    SUM(FT.CUR_AMT) AS TOTAL_DEBT,
    COUNT(DISTINCT CASE WHEN AL.ALERT_TYPE_CD IS NOT NULL THEN AL.ALERT_TYPE_CD END) AS ACTIVE_ALERT_COUNT,
    MAX(B.CRE_DTTM) AS LAST_BILL_CREATED_DTTM
FROM CISADM.CI_ACCT A
JOIN CISADM.CI_SA SA
  ON SA.ACCT_ID = A.ACCT_ID
 AND NULLIF(TRIM(SA.SA_STATUS_FLG), '') = '20'
JOIN CISADM.CI_FT FT
  ON FT.SA_ID = SA.SA_ID
 AND FT.FREEZE_SW = 'Y'
 AND FT.NOT_IN_ARS_SW = 'N'
 AND FT.FT_TYPE_FLG NOT IN ('PS', 'PX')
 AND FT.ARS_DT IS NOT NULL
LEFT JOIN CISADM.CI_ACCT_ALERT AL
  ON AL.ACCT_ID = A.ACCT_ID
 AND :end_ts BETWEEN AL.START_DT AND NVL(AL.END_DT, :end_ts)
LEFT JOIN CISADM.CI_BILL B
  ON B.ACCT_ID = A.ACCT_ID
 AND B.BILL_DT >= :start_ts
 AND B.BILL_DT <  :end_ts
WHERE (:acct_id IS NULL OR A.ACCT_ID = :acct_id)
GROUP BY A.ACCT_ID, A.COLL_CL_CD
HAVING SUM(FT.CUR_AMT) > 0
ORDER BY DEBT_OVER_60 DESC;

--------------------------------------------------------------------------------
-- Use Case 2: New Service Pipeline Aging (Operations SLA)
-- Business value:
--   Detect pending-to-active conversion delays before they create billing lag.
--------------------------------------------------------------------------------
SELECT
    SA.ACCT_ID,
    SA.SA_ID,
    NULLIF(TRIM(SA.SA_STATUS_FLG), '') AS SA_STATUS_FLG,
    SA.CRE_DTTM,
    SA.START_DT,
    TRUNC(:end_ts) - TRUNC(SA.CRE_DTTM) AS DAYS_SINCE_CREATED
FROM CISADM.CI_SA SA
WHERE NULLIF(TRIM(SA.SA_STATUS_FLG), '') IN ('10', '20')
  AND SA.CRE_DTTM >= :start_ts
  AND SA.CRE_DTTM <  :end_ts
  AND (:acct_id IS NULL OR SA.ACCT_ID = :acct_id)
ORDER BY DAYS_SINCE_CREATED DESC;

--------------------------------------------------------------------------------
-- Use Case 3: Cashiering Reconciliation Exceptions
-- Business value:
--   Catch payment events missing valid deposit controls before close.
--------------------------------------------------------------------------------
SELECT
    P.ACCT_ID,
    PE.PAY_EVENT_ID,
    PE.CRE_DTTM,
    NVL(P.PAY_AMT, 0) AS PAY_AMT,
    PT.TENDER_TYPE_CD,
    PT.TNDR_STATUS_FLG,
    TC.TNDR_SOURCE_CD,
    DC.DEP_CTL_ID,
    DC.DEP_CTL_STATUS_FLG
FROM CISADM.CI_PAY_EVENT PE
JOIN CISADM.CI_PAY P
  ON P.PAY_EVENT_ID = PE.PAY_EVENT_ID
JOIN CISADM.CI_PAY_TNDR PT
  ON PT.PAY_EVENT_ID = PE.PAY_EVENT_ID
LEFT JOIN CISADM.CI_TNDR_CTL TC
  ON TC.TNDR_CTL_ID = PT.TNDR_CTL_ID
LEFT JOIN CISADM.CI_DEP_CTL DC
  ON DC.DEP_CTL_ID = TC.DEP_CTL_ID
WHERE PE.CRE_DTTM >= :start_ts
  AND PE.CRE_DTTM <  :end_ts
  AND (:acct_id IS NULL OR P.ACCT_ID = :acct_id)
  AND (DC.DEP_CTL_ID IS NULL OR NULLIF(TRIM(DC.DEP_CTL_STATUS_FLG), '') <> '25')
ORDER BY PE.CRE_DTTM DESC;

--------------------------------------------------------------------------------
-- Use Case 4: Customer Contact Letter Readiness
-- Business value:
--   Ensure letters are printable from contact events with valid templates and
--   recipient details.
--------------------------------------------------------------------------------
SELECT
    CC.CC_ID,
    CC.ACCT_ID,
    CC.CC_DTTM,
    CC.LTR_TMPL_CD,
    NULLIF(TRIM(PN.ENTITY_NAME), '') AS CONTACT_NAME,
    NULLIF(TRIM(PR.ADDRESS1), '') AS ADDRESS1,
    CASE
      WHEN LT.LTR_TMPL_CD IS NULL THEN 'MISSING_TEMPLATE'
      WHEN NULLIF(TRIM(PN.ENTITY_NAME), '') IS NULL THEN 'MISSING_NAME'
      WHEN NULLIF(TRIM(PR.ADDRESS1), '') IS NULL THEN 'MISSING_ADDRESS'
      ELSE 'READY'
    END AS LETTER_READINESS
FROM CISADM.CI_CC CC
LEFT JOIN CISADM.CI_LETTER_TMPL LT
  ON LT.LTR_TMPL_CD = CC.LTR_TMPL_CD
LEFT JOIN CISADM.CI_PER_NAME PN
  ON PN.PER_ID = CC.PER_ID
 AND PN.PRIM_NAME_SW = 'Y'
LEFT JOIN CISADM.CI_PREM PR
  ON PR.PREM_ID = CC.PREM_ID
WHERE CC.PRINT_LETTER_SW = 'Y'
  AND CC.CC_DTTM >= :start_ts
  AND CC.CC_DTTM <  :end_ts
  AND (:acct_id IS NULL OR CC.ACCT_ID = :acct_id)
ORDER BY CC.CC_DTTM DESC;

--------------------------------------------------------------------------------
-- Explain plan template (copy for any use case above)
--------------------------------------------------------------------------------
-- EXPLAIN PLAN FOR
-- <paste selected query here>;
--
-- SELECT *
-- FROM TABLE(DBMS_XPLAN.DISPLAY(NULL, NULL, 'BASIC +PREDICATE +ALIAS +NOTE'));

