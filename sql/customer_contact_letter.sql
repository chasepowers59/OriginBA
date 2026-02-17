-- GOVERNED: Customer Contact Letter Dataset (Jaspersoft-ready, read-only)
-- Purpose: Print customer contact letters directly from CI_CC records where letter printing is enabled.
-- Bind variables:
--   :cc_id      VARCHAR2 (preferred when printing one exact letter/contact event)
--   :acct_id    VARCHAR2 (optional fallback filter)
--   :start_ts   TIMESTAMP (optional fallback filter)
--   :end_ts     TIMESTAMP (optional fallback filter)
--
-- Estimated impact:
--   - By CC_ID: low I/O, index lookup expected.
--   - By ACCT_ID + date window: medium I/O depending on event volume.
--
-- Rollback plan:
--   1) Revert to previous report SQL.
--   2) Remove any optional index introduced for this report.
--   3) Compare plan hash and elapsed time with baseline.

SELECT
    CC.CC_ID,
    CC.ACCT_ID,
    CC.PER_ID,
    CC.PREM_ID,
    CC.CC_DTTM,
    CC.CC_TYPE_CD,
    CC.CC_CL_CD,
    CC.CONTACT_METH_FLG,
    CC.PRINT_LETTER_SW,
    CC.LETTER_PRINT_DTTM,
    CC.LTR_TMPL_CD,
    NULLIF(TRIM(PN.ENTITY_NAME), '') AS CONTACT_NAME,
    NULLIF(TRIM(PR.ADDRESS1), '') AS ADDRESS1,
    NULLIF(TRIM(PR.ADDRESS2), '') AS ADDRESS2,
    NULLIF(TRIM(PR.ADDRESS3), '') AS ADDRESS3,
    NULLIF(TRIM(PR.ADDRESS4), '') AS ADDRESS4,
    NULLIF(TRIM(PR.CITY), '') AS CITY,
    NULLIF(TRIM(PR.STATE), '') AS STATE,
    NULLIF(TRIM(PR.POSTAL), '') AS POSTAL,
    NULLIF(TRIM(CC.DESCRLONG), '') AS LETTER_BODY_TEXT
FROM CISADM.CI_CC CC
LEFT JOIN CISADM.CI_PER_NAME PN
  ON PN.PER_ID = CC.PER_ID
 AND PN.PRIM_NAME_SW = 'Y'
LEFT JOIN CISADM.CI_PREM PR
  ON PR.PREM_ID = CC.PREM_ID
WHERE CC.PRINT_LETTER_SW = 'Y'
  AND (
      ( :cc_id IS NOT NULL AND CC.CC_ID = :cc_id )
      OR
      ( :cc_id IS NULL
        AND :acct_id IS NOT NULL
        AND CC.ACCT_ID = :acct_id
        AND CC.CC_DTTM >= :start_ts
        AND CC.CC_DTTM <  :end_ts
      )
  )
ORDER BY CC.CC_DTTM DESC;

--------------------------------------------------------------------------------
-- Explain plan + xplan
--------------------------------------------------------------------------------
EXPLAIN PLAN FOR
SELECT
    CC.CC_ID,
    CC.ACCT_ID,
    CC.PER_ID,
    CC.PREM_ID,
    CC.CC_DTTM,
    CC.CC_TYPE_CD,
    CC.CC_CL_CD,
    CC.CONTACT_METH_FLG,
    CC.PRINT_LETTER_SW,
    CC.LETTER_PRINT_DTTM,
    CC.LTR_TMPL_CD
FROM CISADM.CI_CC CC
WHERE CC.PRINT_LETTER_SW = 'Y'
  AND (
      ( :cc_id IS NOT NULL AND CC.CC_ID = :cc_id )
      OR
      ( :cc_id IS NULL
        AND :acct_id IS NOT NULL
        AND CC.ACCT_ID = :acct_id
        AND CC.CC_DTTM >= :start_ts
        AND CC.CC_DTTM <  :end_ts
      )
  );

SELECT *
FROM TABLE(DBMS_XPLAN.DISPLAY(NULL, NULL, 'BASIC +PREDICATE +ALIAS +NOTE'));

--------------------------------------------------------------------------------
-- Optional index recommendations (evaluate in DEV/QA only)
--------------------------------------------------------------------------------
-- CREATE INDEX IX_CI_CC_PRINT_CCID ON CISADM.CI_CC (PRINT_LETTER_SW, CC_ID);
-- CREATE INDEX IX_CI_CC_ACCT_DTTM ON CISADM.CI_CC (ACCT_ID, CC_DTTM);
