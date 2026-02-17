-- GOVERNED: Bankruptcy Risk Payment Monitor
-- Source: S_BKRPTCY_payments.sql
-- Used by: pipeline/fetch_usage.py (_QUERY_BANKRUPTCY_MONITOR); also for Jaspersoft JDBC evidence table
-- Value: Legal/risk mitigation; tracks payments on accounts with active BNKRTPCY alert

SELECT DISTINCT
    acct.acct_id,
    pym.ars_dt,
    pym.pym_amt
FROM cisadm.ci_acct acct
INNER JOIN cisadm.ci_acct_alert alert ON acct.acct_id = alert.acct_id
    AND alert.alert_type_cd = 'BNKRTPCY'
    AND SYSDATE BETWEEN alert.start_dt AND NVL(alert.end_dt, SYSDATE)
INNER JOIN (
    SELECT sa.acct_id, ft.ars_dt, NVL(SUM(ft.cur_amt),0) AS pym_amt
    FROM cisadm.ci_ft ft, cisadm.ci_sa sa
    WHERE sa.sa_id = ft.sa_id AND ft.ft_type_flg = 'PS' AND ft.freeze_sw = 'Y'
    GROUP BY sa.acct_id, ft.ars_dt
) pym ON acct.acct_id = pym.acct_id
WHERE pym.ars_dt BETWEEN SYSDATE - 60 AND SYSDATE;
