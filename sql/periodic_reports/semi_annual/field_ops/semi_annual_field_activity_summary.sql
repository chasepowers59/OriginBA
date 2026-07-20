-- PERIODIC_REPORT: S6 semi_annual_field_activity_summary
-- FREQUENCY: semi_annual
-- WORKSTREAM: field_ops
-- GRAIN: ACTIVITY_TYPE_CD + BO_STATUS_CD
-- WINDOW: previous six full calendar months (activity create date)
-- SOURCE: FIELD_ACTIVITY_RPT_CURR
-- NOTE: requires FIELD_ACTIVITY_RPT_CURR snapshot deployment

SELECT fa.activity_type_cd,
       fa.activity_type_desc,
       fa.bo_status_cd,
       fa.bo_status_desc,
       COUNT(*) AS activity_count
FROM cisadm.field_activity_rpt_curr fa
WHERE fa.act_cre_dttm >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -6)
  AND fa.act_cre_dttm < TRUNC(SYSDATE, 'MM')
  AND fa.d1_activity_id NOT LIKE 'ODEV%'
GROUP BY fa.activity_type_cd, fa.activity_type_desc,
         fa.bo_status_cd, fa.bo_status_desc
ORDER BY COUNT(*) DESC;
