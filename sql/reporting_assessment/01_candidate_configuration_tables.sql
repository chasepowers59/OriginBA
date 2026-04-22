PROMPT ============================================================
PROMPT Candidate CISADM configuration tables
PROMPT ============================================================

WITH candidate_tables AS (
    SELECT
        t.owner,
        t.table_name,
        t.num_rows,
        t.last_analyzed,
        CASE
            WHEN t.table_name LIKE '%\_L' ESCAPE '\' THEN 'language_lookup'
            WHEN t.table_name LIKE '%TYPE%' THEN 'type_or_classification'
            WHEN t.table_name LIKE '%LOOKUP%' THEN 'lookup'
            WHEN t.table_name LIKE '%CYC%' THEN 'cycle_or_schedule'
            WHEN t.table_name LIKE '%STATUS%' THEN 'status'
            WHEN t.table_name LIKE '%UOM%' OR t.table_name LIKE '%TOU%' OR t.table_name LIKE '%SQI%' THEN 'unit_or_determinant'
            ELSE 'other_config_candidate'
        END AS candidate_reason
    FROM all_tables t
    WHERE t.owner = 'CISADM'
      AND (
            t.table_name LIKE 'CI%\_L' ESCAPE '\'
         OR t.table_name LIKE 'D1%\_L' ESCAPE '\'
         OR t.table_name LIKE 'F1%\_L' ESCAPE '\'
         OR t.table_name LIKE '%TYPE%'
         OR t.table_name LIKE '%LOOKUP%'
         OR t.table_name LIKE '%CYC%'
         OR t.table_name LIKE '%UOM%'
         OR t.table_name LIKE '%TOU%'
         OR t.table_name LIKE '%SQI%'
         OR t.table_name LIKE '%RS%'
      )
)
SELECT
    owner,
    table_name,
    candidate_reason,
    num_rows,
    last_analyzed
FROM candidate_tables
ORDER BY
    candidate_reason,
    table_name;

WITH candidate_tables AS (
    SELECT table_name
    FROM all_tables
    WHERE owner = 'CISADM'
      AND (
            table_name LIKE 'CI%\_L' ESCAPE '\'
         OR table_name LIKE 'D1%\_L' ESCAPE '\'
         OR table_name LIKE 'F1%\_L' ESCAPE '\'
         OR table_name LIKE '%TYPE%'
         OR table_name LIKE '%LOOKUP%'
         OR table_name LIKE '%CYC%'
         OR table_name LIKE '%UOM%'
         OR table_name LIKE '%TOU%'
         OR table_name LIKE '%SQI%'
         OR table_name LIKE '%RS%'
      )
)
SELECT
    c.table_name,
    c.column_id,
    c.column_name,
    c.data_type,
    c.data_length
FROM all_tab_columns c
INNER JOIN candidate_tables t
    ON t.table_name = c.table_name
WHERE c.owner = 'CISADM'
ORDER BY
    c.table_name,
    c.column_id;
