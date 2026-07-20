-- PERIODIC_REPORT: Q6 quarterly_workflow_open_aging
-- FREQUENCY: quarterly
-- WORKSTREAM: workflow
-- GRAIN: aging bucket (open todos only)
-- WINDOW: todos created in previous full calendar quarter, still open
-- SOURCE: WORKFLOW_QUEUE_RPT_CURR

SELECT CASE
         WHEN wq.days_old IS NULL THEN 'UNKNOWN'
         WHEN wq.days_old < 30 THEN '0-29 days'
         WHEN wq.days_old < 60 THEN '30-59 days'
         WHEN wq.days_old < 90 THEN '60-89 days'
         ELSE '90+ days'
       END AS aging_bucket,
       wq.td_type_cd,
       wq.td_type_desc,
       COUNT(*) AS open_item_count
FROM cisadm.workflow_queue_rpt_curr wq
WHERE wq.queue_source = 'TODO'
  AND NULLIF(TRIM(wq.entry_status_flg), '') IN ('O', 'W')
  AND wq.td_cre_dttm >= TRUNC(ADD_MONTHS(SYSDATE, -3), 'Q')
  AND wq.td_cre_dttm < TRUNC(SYSDATE, 'Q')
  AND (wq.td_entry_id IS NULL OR wq.td_entry_id NOT LIKE 'ODEV%')
GROUP BY CASE
           WHEN wq.days_old IS NULL THEN 'UNKNOWN'
           WHEN wq.days_old < 30 THEN '0-29 days'
           WHEN wq.days_old < 60 THEN '30-59 days'
           WHEN wq.days_old < 90 THEN '60-89 days'
           ELSE '90+ days'
         END,
         wq.td_type_cd, wq.td_type_desc
ORDER BY aging_bucket, wq.td_type_cd;
