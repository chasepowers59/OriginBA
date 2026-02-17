-- GOVERNED: SmartCity 9 Workstream KPI Pack (Jaspersoft-ready, read-only)
-- Source of truth:
--   - output/workstream_reporting_dictionary.json
--   - output/domain_designs_metadata.json (from Domain Designs.xlsx)
-- Binds:
--   :client_id  VARCHAR2 (optional; maps to CIS division when available)
--   :start_ts   TIMESTAMP
--   :end_ts     TIMESTAMP

SELECT WORKSTREAM_NAME, KPI_NAME, KPI_VALUE
FROM (
    -- 1) Billing: Open bills in window
    SELECT 'billing' AS WORKSTREAM_NAME,
           'OPEN_BILLS' AS KPI_NAME,
           COUNT(*) AS KPI_VALUE
    FROM CISADM.CI_BILL B
    JOIN CISADM.CI_ACCT A ON A.ACCT_ID = B.ACCT_ID
    WHERE B.CRE_DTTM >= :start_ts
      AND B.CRE_DTTM <  :end_ts
      AND NULLIF(TRIM(B.BILL_STAT_FLG), '') <> '60'
      AND (:client_id IS NULL OR A.CIS_DIVISION = :client_id)

    UNION ALL

    -- 2) Cashiering: unresolved tender/deposit controls
    SELECT 'cashiering',
           'UNRESOLVED_TENDER_CONTROLS',
           COUNT(*)
    FROM CISADM.CI_PAY_EVENT PE
    JOIN CISADM.CI_PAY P ON P.PAY_EVENT_ID = PE.PAY_EVENT_ID
    JOIN CISADM.CI_PAY_TNDR PT ON PT.PAY_EVENT_ID = PE.PAY_EVENT_ID
    LEFT JOIN CISADM.CI_TNDR_CTL TC ON TC.TNDR_CTL_ID = PT.TNDR_CTL_ID
    LEFT JOIN CISADM.CI_DEP_CTL DC ON DC.DEP_CTL_ID = TC.DEP_CTL_ID
    JOIN CISADM.CI_ACCT A ON A.ACCT_ID = P.ACCT_ID
    WHERE PE.CRE_DTTM >= :start_ts
      AND PE.CRE_DTTM <  :end_ts
      AND (:client_id IS NULL OR A.CIS_DIVISION = :client_id)
      AND (DC.DEP_CTL_ID IS NULL OR NULLIF(TRIM(DC.DEP_CTL_STATUS_FLG), '') <> '25')

    UNION ALL

    -- 3) Meter Ops: install events recorded in window
    SELECT 'meter_ops',
           'INSTALL_EVENTS',
           COUNT(*)
    FROM CISADM.D1_INSTALL_EVT IE
    WHERE IE.D1_INSTALL_DTTM >= :start_ts
      AND IE.D1_INSTALL_DTTM <  :end_ts

    UNION ALL

    -- 4) Customer Ops: printable contact defects
    SELECT 'customer_ops',
           'CONTACT_LETTER_DEFECTS',
           COUNT(*)
    FROM CISADM.CI_CC CC
    JOIN CISADM.CI_ACCT A ON A.ACCT_ID = CC.ACCT_ID
    LEFT JOIN CISADM.CI_LETTER_TMPL LT ON LT.LTR_TMPL_CD = CC.LTR_TMPL_CD
    LEFT JOIN CISADM.CI_PER_NAME PN ON PN.PER_ID = CC.PER_ID AND PN.PRIM_NAME_SW = 'Y'
    LEFT JOIN CISADM.CI_PREM PR ON PR.PREM_ID = CC.PREM_ID
    WHERE CC.PRINT_LETTER_SW = 'Y'
      AND CC.CC_DTTM >= :start_ts
      AND CC.CC_DTTM <  :end_ts
      AND (:client_id IS NULL OR A.CIS_DIVISION = :client_id)
      AND (
          LT.LTR_TMPL_CD IS NULL
          OR NULLIF(TRIM(PN.ENTITY_NAME), '') IS NULL
          OR NULLIF(TRIM(PR.ADDRESS1), '') IS NULL
      )

    UNION ALL

    -- 5) New Services: pending SAs whose start date is in the past
    SELECT 'new_services',
           'STALE_PENDING_SA',
           COUNT(*)
    FROM CISADM.CI_SA SA
    JOIN CISADM.CI_ACCT A ON A.ACCT_ID = SA.ACCT_ID
    WHERE NULLIF(TRIM(SA.SA_STATUS_FLG), '') = '10'
      AND SA.START_DT IS NOT NULL
      AND TRUNC(SA.START_DT) < TRUNC(:end_ts)
      AND (:client_id IS NULL OR A.CIS_DIVISION = :client_id)

    UNION ALL

    -- 6) Finance: FT missing GL distribution status in window
    SELECT 'finance',
           'FT_MISSING_GL_STATUS',
           COUNT(*)
    FROM CISADM.CI_FT FT
    JOIN CISADM.CI_SA SA ON SA.SA_ID = FT.SA_ID
    JOIN CISADM.CI_ACCT A ON A.ACCT_ID = SA.ACCT_ID
    WHERE FT.CRE_DTTM >= :start_ts
      AND FT.CRE_DTTM <  :end_ts
      AND NULLIF(TRIM(FT.GL_DISTRIB_STATUS), '') IS NULL
      AND (:client_id IS NULL OR A.CIS_DIVISION = :client_id)

    UNION ALL

    -- 7) Common: inactive lookup values
    SELECT 'common',
           'INACTIVE_LOOKUP_VALUES',
           COUNT(*)
    FROM CISADM.CI_LOOKUP_VAL LV
    WHERE NULLIF(TRIM(LV.EFF_STATUS), '') <> 'A'

    UNION ALL

    -- 8) Debt Management: debt over 60 days
    SELECT 'debt_mgmt',
           'DEBT_OVER_60',
           NVL(SUM(CASE
                     WHEN FT.FREEZE_SW = 'Y'
                      AND FT.NOT_IN_ARS_SW = 'N'
                      AND FT.FT_TYPE_FLG NOT IN ('PS', 'PX')
                      AND FT.ARS_DT IS NOT NULL
                      AND (TRUNC(:end_ts) - FT.ARS_DT) > 60
                     THEN FT.CUR_AMT
                     ELSE 0
                   END), 0)
    FROM CISADM.CI_FT FT
    JOIN CISADM.CI_SA SA ON SA.SA_ID = FT.SA_ID
    JOIN CISADM.CI_ACCT A ON A.ACCT_ID = SA.ACCT_ID
    WHERE FT.CRE_DTTM >= :start_ts
      AND FT.CRE_DTTM <  :end_ts
      AND (:client_id IS NULL OR A.CIS_DIVISION = :client_id)

    UNION ALL

    -- 9) Field Ops: service points without install event linkage
    SELECT 'field_ops',
           'SP_WITHOUT_INSTALL_EVENT',
           COUNT(*)
    FROM CISADM.CI_SP SP
    LEFT JOIN CISADM.D1_INSTALL_EVT IE ON IE.D1_SP_ID = SP.SP_ID
    WHERE IE.D1_SP_ID IS NULL
)
ORDER BY WORKSTREAM_NAME, KPI_NAME;

-- EXPLAIN PLAN FOR
-- SELECT ... (paste one targeted workstream query from above);
-- SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY(NULL, NULL, 'BASIC +PREDICATE +ALIAS +NOTE'));
