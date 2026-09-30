-- PERIODIC_REPORT: A7 annual_workflow_volume_by_type
-- FREQUENCY: annual
-- WORKSTREAM: workflow
-- GRAIN: TD_TYPE_CD + ENTRY_STATUS_FLG
-- WINDOW: previous full calendar year (todo create date)
-- SOURCE: WORKFLOW_QUEUE_RPT_CURR
-- GOVERNED: exclude ODEV, TODO queue source only

SELECT wq.td_type_cd,
       wq.td_type_desc,
       wq.entry_status_flg,
       wq.entry_status_desc,
       COUNT(*) AS queue_item_count
FROM cisadm.workflow_queue_rpt_curr wq
WHERE wq.queue_source = 'TODO'
  AND wq.td_cre_dttm >= TRUNC(ADD_MONTHS(SYSDATE, -12), 'YYYY')
  AND wq.td_cre_dttm < TRUNC(SYSDATE, 'YYYY')
  AND (wq.td_entry_id IS NULL OR wq.td_entry_id NOT LIKE 'ODEV%')
GROUP BY wq.td_type_cd, wq.td_type_desc,
         wq.entry_status_flg, wq.entry_status_desc
ORDER BY COUNT(*) DESC;
