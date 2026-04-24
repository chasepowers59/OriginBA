-- Purpose:
-- Return active C2M accounts enrolled in OCX that are on EBILL and have an
-- active email communication route. Captured from Jira support work for reuse.
--
-- Business intent:
-- Support one-time or recurring outreach to active paperless customers, such as
-- notifying EBILL customers about bill inserts that are otherwise mailed with
-- paper bills.
--
-- Current known enrollment logic:
-- - OCX enrollment is indicated by CI_ACCT_ALERT.ALERT_TYPE_CD = 'ACCTENRL'
-- - Paperless is indicated by CI_ACCT_PER.BILL_RTE_TYPE_CD = 'EBILL'
-- - Active email route is indicated by:
--     C1_PER_CONTDET.CND_ACTINACT_FLG = 'C1AC'
--     C1_COMM_RTE_TYPE.COMM_RTE_METH_FLG = 'EMAIL'
-- - Active service is constrained by CI_SA.SA_STATUS_FLG in ('10','20','30','50')
--
-- Source:
-- Shared in support follow-up for CX / paperless billing communication review
-- on 2026-04-23.

SELECT DISTINCT
       acctper.per_id,
       acct.acct_id,
       pc.contact_value
FROM cisadm.ci_acct acct
JOIN cisadm.ci_acct_alert acctalert
     ON acctalert.acct_id = acct.acct_id
JOIN cisadm.ci_acct_per acctper
     ON acctper.acct_id = acct.acct_id
JOIN cisadm.c1_per_contdet pc
     ON pc.per_id = acctper.per_id
JOIN cisadm.c1_comm_rte_type pct
     ON pct.comm_rte_type_cd = pc.comm_rte_type_cd
WHERE acctalert.alert_type_cd = 'ACCTENRL'
  AND (acctalert.end_dt IS NULL OR acctalert.end_dt > SYSDATE)
  AND acctper.bill_rte_type_cd = 'EBILL'
  AND pc.cnd_actinact_flg = 'C1AC'
  AND pct.comm_rte_meth_flg = 'EMAIL'
  AND acctper.main_cust_sw = 'Y'
  AND EXISTS (
      SELECT 1
      FROM cisadm.ci_sa sa
      WHERE sa.acct_id = acct.acct_id
        AND sa.sa_status_flg IN ('10', '20', '30', '50')
  )
ORDER BY acct.acct_id, acctper.per_id, pc.contact_value;
