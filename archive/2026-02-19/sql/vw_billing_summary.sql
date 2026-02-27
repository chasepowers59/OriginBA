-- Billing & Rates domain view (logical definition for reporting/Jaspersoft)
-- Source-of-truth: CISADM.CI_BILL (header), CISADM.CI_BSEG (segments)
-- Filters: FREEZE_SW = 'Y' is enforced in CI_FT-level facts; here we focus on recent bills.

SELECT
  bl.BILL_ID,
  bl.BILL_DT,
  bl.DUE_DT,
  bl.BILL_STAT_FLG,
  bl.ACCT_ID,
  bl.BILL_CYC_CD,
  bl.CRE_DTTM
FROM CISADM.CI_BILL bl
WHERE bl.BILL_DT >= ADD_MONTHS(TRUNC(SYSDATE), -3)
  AND bl.BILL_DT < TRUNC(SYSDATE) + 1;

