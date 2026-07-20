-- Discovery: workflow / to-do profile (informational).

PROMPT === Workflow: todo status distribution ===

SELECT entry_status_flg, COUNT(*) AS cnt
FROM cisadm.ci_td_entry
GROUP BY entry_status_flg
ORDER BY cnt DESC;

PROMPT === Workflow: open/working assignee population ===

SELECT COUNT(*) AS open_working_cnt,
       SUM(CASE WHEN TRIM(assigned_to) IS NULL THEN 1 ELSE 0 END) AS blank_assignee,
       SUM(CASE WHEN TRIM(assigned_to) IS NOT NULL THEN 1 ELSE 0 END) AS has_assignee
FROM cisadm.ci_td_entry
WHERE entry_status_flg IN ('O', 'W');

PROMPT === Workflow: top todo types ===

SELECT td_type_cd, entry_status_flg, COUNT(*) AS cnt
FROM cisadm.ci_td_entry
GROUP BY td_type_cd, entry_status_flg
ORDER BY cnt DESC
FETCH FIRST 15 ROWS ONLY;
