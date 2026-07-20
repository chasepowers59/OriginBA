-- WARN gate: open/working todos mostly unassigned (breaks assignee filters).

PROMPT === Gate 07: todo assignee population (WARN if >95% blank) ===

SELECT '07_todo_blank_assignee' AS check_id,
       'WARN' AS severity,
       'Open/working todos with blank ASSIGNED_TO' AS detail,
       TO_CHAR(ROUND(100 * blank_cnt / NULLIF(total_cnt, 0), 1)) || '%' AS metric
FROM (
  SELECT COUNT(*) AS total_cnt,
         SUM(CASE WHEN TRIM(assigned_to) IS NULL THEN 1 ELSE 0 END) AS blank_cnt
  FROM cisadm.ci_td_entry
  WHERE entry_status_flg IN ('O', 'W')
)
WHERE total_cnt > 0
  AND blank_cnt / total_cnt > 0.95;
