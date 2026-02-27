-- customer_contact_print_check.sql
-- Purpose: Validate whether customer-contact letters are printable and explain blockers.
-- Datasource target: ORIGIN_DEV_DS (repository-managed in JRS)
-- Bind variables expected from Jasper:
--   :CC_ID (VARCHAR2, optional)
--   :ACCT_ID (VARCHAR2, optional)
--   :START_TS (TIMESTAMP, optional)
--   :END_TS (TIMESTAMP, optional)

EXPLAIN PLAN FOR
SELECT
    cc.cc_id,
    cc.acct_id,
    cc.per_id,
    cc.prem_id,
    cc.cc_dttm,
    cc.cc_type_cd,
    cc.cc_cl_cd,
    cc.contact_meth_flg,
    cc.print_letter_sw,
    cc.ltr_tmpl_cd,
    cc.letter_print_dttm,
    NULLIF(TRIM(pn.entity_name), '') AS recipient_name,
    NULLIF(TRIM(pr.address1), '') AS address1,
    NULLIF(TRIM(pr.address2), '') AS address2,
    NULLIF(TRIM(pr.city), '') AS city,
    NULLIF(TRIM(pr.state), '') AS state,
    NULLIF(TRIM(pr.postal), '') AS postal,
    CASE
        WHEN NVL(TRIM(cc.print_letter_sw), 'N') <> 'Y' THEN 'NOT_PRINTABLE'
        WHEN NVL(TRIM(cc.ltr_tmpl_cd), '') = '' THEN 'NOT_PRINTABLE'
        WHEN NVL(TRIM(pn.entity_name), '') = '' THEN 'NOT_PRINTABLE'
        WHEN NVL(TRIM(pr.address1), '') = '' OR NVL(TRIM(pr.city), '') = '' OR NVL(TRIM(pr.state), '') = '' OR NVL(TRIM(pr.postal), '') = '' THEN 'NOT_PRINTABLE'
        ELSE 'PRINTABLE'
    END AS print_status,
    CASE
        WHEN NVL(TRIM(cc.print_letter_sw), 'N') <> 'Y' THEN 'Print switch is not Y'
        WHEN NVL(TRIM(cc.ltr_tmpl_cd), '') = '' THEN 'Missing letter template code'
        WHEN NVL(TRIM(pn.entity_name), '') = '' THEN 'Missing recipient name'
        WHEN NVL(TRIM(pr.address1), '') = '' OR NVL(TRIM(pr.city), '') = '' OR NVL(TRIM(pr.state), '') = '' OR NVL(TRIM(pr.postal), '') = '' THEN 'Incomplete mailing address'
        ELSE 'Ready to print'
    END AS block_reason
FROM CISADM.CI_CC cc
LEFT JOIN CISADM.CI_PER_NAME pn
  ON pn.per_id = cc.per_id
 AND pn.prim_name_sw = 'Y'
LEFT JOIN CISADM.CI_PREM pr
  ON pr.prem_id = cc.prem_id
WHERE ($P{CC_ID} IS NULL OR cc.cc_id = $P{CC_ID})
  AND ($P{ACCT_ID} IS NULL OR cc.acct_id = $P{ACCT_ID})
  AND ($P{START_TS} IS NULL OR cc.cc_dttm >= $P{START_TS})
  AND ($P{END_TS} IS NULL OR cc.cc_dttm < $P{END_TS})
ORDER BY cc.cc_dttm DESC;

SELECT * FROM TABLE(DBMS_XPLAN.DISPLAY(NULL, NULL, 'ALL'));

-- Index recommendations (evaluate first in DEV/QA):
-- 1) CREATE INDEX CISADM.IDX_CI_CC_ACCT_DTTM ON CISADM.CI_CC (ACCT_ID, CC_DTTM);
-- 2) CREATE INDEX CISADM.IDX_CI_CC_PRINT_DTTM ON CISADM.CI_CC (PRINT_LETTER_SW, CC_DTTM);
-- 3) Ensure CI_PER_NAME has efficient access path for (PER_ID, PRIM_NAME_SW).
