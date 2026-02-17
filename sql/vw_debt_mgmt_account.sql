-- Debt Management domain view (collections, arrears follow-up, payment plans)
-- Source-of-truth: CISADM.CI_ACCT (collection class, credit review dates), CISADM.CI_FT (arrears facts).

SELECT
  a.ACCT_ID,
  a.COLL_CL_CD,
  a.CR_REVIEW_DT,
  a.POSTPONE_CR_RVW_DT
FROM CISADM.CI_ACCT a;

