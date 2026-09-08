-- PERIODIC_REPORT: Q7 quarterly_usage_processing_volume
-- FREQUENCY: quarterly
-- WORKSTREAM: usage
-- GRAIN: BO_STATUS_CD
-- WINDOW: previous full calendar quarter (usage create date)
-- SOURCE: D1_USAGE_RPT_CURR

SELECT u.bo_status_cd,
       u.bo_status_desc,
       COUNT(*) AS usage_count
FROM cisadm.d1_usage_rpt_curr u
WHERE u.usage_cre_dttm >= TRUNC(ADD_MONTHS(SYSDATE, -3), 'Q')
  AND u.usage_cre_dttm < TRUNC(SYSDATE, 'Q')
  AND (u.acct_id IS NULL OR u.acct_id NOT LIKE 'ODEV%')
GROUP BY u.bo_status_cd, u.bo_status_desc
ORDER BY COUNT(*) DESC;
