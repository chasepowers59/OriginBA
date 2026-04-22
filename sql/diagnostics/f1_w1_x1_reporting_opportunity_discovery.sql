-- f1_w1_x1_reporting_opportunity_discovery.sql
-- Read-only discovery pack for framework / asset / cross-product tables in CISADM.
-- Purpose:
--   1) inventory F1_ / W1_ / X1_ objects
--   2) profile columns and likely reporting role
--   3) find candidate joins back to CI_ / D1_ / C1_
--   4) surface likely reporting opportunities
--   5) optionally print actual row counts and recent dates for top tables
--
-- SQL Developer / SQLcl usage:
--   DEFINE schema_owner = CISADM
--   DEFINE profile_table_limit = 40
--   SET SERVEROUTPUT ON SIZE UNLIMITED
--
-- Notes:
--   - This script is read-only.
--   - The final PL/SQL block can be the heaviest section because it executes
--     dynamic counts against discovered tables.

DEFINE schema_owner = CISADM
DEFINE profile_table_limit = 40

PROMPT ============================================================
PROMPT 1. OBJECT INVENTORY: F1_ / W1_ / X1_ TABLES AND VIEWS
PROMPT ============================================================

WITH target_objects AS (
  SELECT
    o.owner,
    o.object_name,
    o.object_type
  FROM all_objects o
  WHERE o.owner = UPPER('&schema_owner')
    AND o.object_type IN ('TABLE', 'VIEW', 'MATERIALIZED VIEW')
    AND REGEXP_LIKE(o.object_name, '^(F1|W1|X1)_')
),
table_stats AS (
  SELECT
    t.owner,
    t.table_name,
    t.num_rows,
    t.blocks,
    t.avg_row_len,
    t.last_analyzed,
    t.partitioned,
    t.temporary
  FROM all_tables t
  WHERE t.owner = UPPER('&schema_owner')
)
SELECT
  o.owner,
  o.object_name,
  o.object_type,
  tc.comments AS object_comment,
  ts.num_rows,
  ts.blocks,
  ts.avg_row_len,
  ts.partitioned,
  ts.temporary,
  ts.last_analyzed
FROM target_objects o
LEFT JOIN all_tab_comments tc
  ON tc.owner = o.owner
 AND tc.table_name = o.object_name
LEFT JOIN table_stats ts
  ON ts.owner = o.owner
 AND ts.table_name = o.object_name
ORDER BY
  o.object_name;

PROMPT ============================================================
PROMPT 2. COLUMN FEATURE PROFILE: WHAT KIND OF REPORTING OBJECT IS EACH TABLE
PROMPT ============================================================

WITH target_columns AS (
  SELECT
    c.owner,
    c.table_name,
    c.column_name,
    c.data_type
  FROM all_tab_columns c
  WHERE c.owner = UPPER('&schema_owner')
    AND REGEXP_LIKE(c.table_name, '^(F1|W1|X1)_')
),
profile AS (
  SELECT
    owner,
    table_name,
    COUNT(*) AS column_count,
    SUM(CASE WHEN REGEXP_LIKE(column_name, '(_ID|_CD|_KEY|^ID$|^CD$)') THEN 1 ELSE 0 END) AS key_col_count,
    SUM(CASE WHEN REGEXP_LIKE(column_name, '(STATUS|STAT|_FLG$|_SW$|STATE|RESULT|OUTCOME)') THEN 1 ELSE 0 END) AS status_col_count,
    SUM(CASE WHEN REGEXP_LIKE(column_name, '(_DT$|_DATE$|_DTTM$|_TS$|_TMSTMP$|_START_|_END_|_CRE_|_UPD_)') THEN 1 ELSE 0 END) AS temporal_col_count,
    SUM(CASE WHEN REGEXP_LIKE(column_name, '(AMT|AMOUNT|QTY|QUANTITY|COUNT|CNT|COST|PRICE|TOTAL|HOURS|DURATION)') THEN 1 ELSE 0 END) AS metric_col_count,
    SUM(CASE WHEN REGEXP_LIKE(column_name, '(DESCR|DESCRIPTION|NAME|LONG_NAME|SHORT_NAME)') THEN 1 ELSE 0 END) AS descriptive_col_count,
    SUM(CASE WHEN REGEXP_LIKE(column_name, '(ACCT_ID|SA_ID|SP_ID|D1_SP_ID|PREM_ID|PER_ID|ASSET_ID|DVC|DEVICE|METER|TSK_ID|WO_|ACTIVITY|INV_|ITEM_|PO_)') THEN 1 ELSE 0 END) AS business_signal_col_count
  FROM target_columns
  GROUP BY
    owner,
    table_name
)
SELECT
  p.owner,
  p.table_name,
  p.column_count,
  p.key_col_count,
  p.status_col_count,
  p.temporal_col_count,
  p.metric_col_count,
  p.descriptive_col_count,
  p.business_signal_col_count,
  CASE
    WHEN REGEXP_LIKE(p.table_name, '(_L$|LOOKUP|TYPE|STATUS)') THEN 'LIKELY_LOOKUP_DIM'
    WHEN p.metric_col_count > 0 AND p.temporal_col_count > 0 THEN 'LIKELY_FACT'
    WHEN p.business_signal_col_count >= 3 AND p.temporal_col_count = 0 AND p.metric_col_count = 0 THEN 'LIKELY_BRIDGE_OR_CONFIG'
    WHEN p.temporal_col_count > 0 AND p.status_col_count > 0 THEN 'LIKELY_PROCESS_OR_EVENT'
    ELSE 'MANUAL_REVIEW'
  END AS likely_reporting_role
FROM profile p
ORDER BY
  likely_reporting_role,
  p.metric_col_count DESC,
  p.temporal_col_count DESC,
  p.table_name;

PROMPT ============================================================
PROMPT 3. THEMATIC OPPORTUNITY SCORING
PROMPT ============================================================

WITH target_objects AS (
  SELECT
    o.owner,
    o.object_name AS table_name,
    tc.comments AS object_comment
  FROM all_objects o
  LEFT JOIN all_tab_comments tc
    ON tc.owner = o.owner
   AND tc.table_name = o.object_name
  WHERE o.owner = UPPER('&schema_owner')
    AND o.object_type IN ('TABLE', 'VIEW', 'MATERIALIZED VIEW')
    AND REGEXP_LIKE(o.object_name, '^(F1|W1|X1)_')
),
themes AS (
  SELECT 'ASSET_LIFECYCLE' AS theme, 'ASSET' AS pattern FROM dual UNION ALL
  SELECT 'ASSET_LIFECYCLE', 'EQUIP' FROM dual UNION ALL
  SELECT 'ASSET_LIFECYCLE', 'INSTALL' FROM dual UNION ALL
  SELECT 'ASSET_LIFECYCLE', 'REMOVE' FROM dual UNION ALL
  SELECT 'ASSET_LIFECYCLE', 'SERIAL' FROM dual UNION ALL
  SELECT 'WORK_EXECUTION', 'WORK' FROM dual UNION ALL
  SELECT 'WORK_EXECUTION', 'TASK' FROM dual UNION ALL
  SELECT 'WORK_EXECUTION', 'TSK' FROM dual UNION ALL
  SELECT 'WORK_EXECUTION', 'ASSIGN' FROM dual UNION ALL
  SELECT 'WORK_EXECUTION', 'SCHED' FROM dual UNION ALL
  SELECT 'WORK_EXECUTION', 'ACTIVITY' FROM dual UNION ALL
  SELECT 'INVENTORY_MATERIALS', 'INVENT' FROM dual UNION ALL
  SELECT 'INVENTORY_MATERIALS', 'STOCK' FROM dual UNION ALL
  SELECT 'INVENTORY_MATERIALS', 'ITEM' FROM dual UNION ALL
  SELECT 'INVENTORY_MATERIALS', 'PART' FROM dual UNION ALL
  SELECT 'INVENTORY_MATERIALS', 'MATERIAL' FROM dual UNION ALL
  SELECT 'PURCHASING_PROCUREMENT', 'PURCH' FROM dual UNION ALL
  SELECT 'PURCHASING_PROCUREMENT', 'PO_' FROM dual UNION ALL
  SELECT 'PURCHASING_PROCUREMENT', 'REQ' FROM dual UNION ALL
  SELECT 'PURCHASING_PROCUREMENT', 'VENDOR' FROM dual UNION ALL
  SELECT 'PURCHASING_PROCUREMENT', 'SUPPLIER' FROM dual UNION ALL
  SELECT 'COSTS_AND_FINANCE', 'COST' FROM dual UNION ALL
  SELECT 'COSTS_AND_FINANCE', 'AMT' FROM dual UNION ALL
  SELECT 'COSTS_AND_FINANCE', 'AMOUNT' FROM dual UNION ALL
  SELECT 'COSTS_AND_FINANCE', 'PRICE' FROM dual UNION ALL
  SELECT 'COSTS_AND_FINANCE', 'GL_' FROM dual UNION ALL
  SELECT 'APPROVAL_AND_GOVERNANCE', 'APPROV' FROM dual UNION ALL
  SELECT 'APPROVAL_AND_GOVERNANCE', 'AUTH' FROM dual UNION ALL
  SELECT 'APPROVAL_AND_GOVERNANCE', 'EXCEPT' FROM dual UNION ALL
  SELECT 'METER_DEVICE_LINKAGE', 'DEVICE' FROM dual UNION ALL
  SELECT 'METER_DEVICE_LINKAGE', 'DVC' FROM dual UNION ALL
  SELECT 'METER_DEVICE_LINKAGE', 'METER' FROM dual UNION ALL
  SELECT 'METER_DEVICE_LINKAGE', 'SP_ID' FROM dual UNION ALL
  SELECT 'METER_DEVICE_LINKAGE', 'D1_SP_ID' FROM dual UNION ALL
  SELECT 'DEPLOYMENT_AND_INTEGRATION', 'MIGR' FROM dual UNION ALL
  SELECT 'DEPLOYMENT_AND_INTEGRATION', 'BNDL' FROM dual UNION ALL
  SELECT 'DEPLOYMENT_AND_INTEGRATION', 'SYNC' FROM dual UNION ALL
  SELECT 'DEPLOYMENT_AND_INTEGRATION', 'INTF' FROM dual UNION ALL
  SELECT 'DEPLOYMENT_AND_INTEGRATION', 'REST' FROM dual UNION ALL
  SELECT 'DEPLOYMENT_AND_INTEGRATION', 'API' FROM dual
),
matches AS (
  SELECT
    th.theme,
    o.table_name,
    'TABLE_NAME' AS signal_source,
    o.table_name AS signal_value
  FROM target_objects o
  JOIN themes th
    ON UPPER(o.table_name) LIKE '%' || th.pattern || '%'
  UNION ALL
  SELECT
    th.theme,
    c.table_name,
    'COLUMN_NAME' AS signal_source,
    c.column_name AS signal_value
  FROM all_tab_columns c
  JOIN themes th
    ON UPPER(c.column_name) LIKE '%' || th.pattern || '%'
  WHERE c.owner = UPPER('&schema_owner')
    AND REGEXP_LIKE(c.table_name, '^(F1|W1|X1)_')
  UNION ALL
  SELECT
    th.theme,
    o.table_name,
    'COMMENT' AS signal_source,
    o.object_comment AS signal_value
  FROM target_objects o
  JOIN themes th
    ON UPPER(NVL(o.object_comment, ' ')) LIKE '%' || th.pattern || '%'
)
SELECT
  m.theme,
  m.table_name,
  COUNT(*) AS signal_count,
  COUNT(DISTINCT m.signal_source) AS signal_source_count,
  MIN(m.signal_value) AS example_signal,
  CASE m.theme
    WHEN 'ASSET_LIFECYCLE' THEN 'Asset inventory, install/remove history, maintenance compliance'
    WHEN 'WORK_EXECUTION' THEN 'Backlog, aging, assignment, completion, SLA'
    WHEN 'INVENTORY_MATERIALS' THEN 'On-hand inventory, stockouts, parts usage'
    WHEN 'PURCHASING_PROCUREMENT' THEN 'PO pipeline, vendor performance, receipt exceptions'
    WHEN 'COSTS_AND_FINANCE' THEN 'Work cost rollups, asset spend, accounting linkage'
    WHEN 'APPROVAL_AND_GOVERNANCE' THEN 'Approval aging, status governance, exception monitoring'
    WHEN 'METER_DEVICE_LINKAGE' THEN 'Meter-to-asset linkage, install lineage, asset health'
    WHEN 'DEPLOYMENT_AND_INTEGRATION' THEN 'Migration, bundle, interface, sync monitoring'
    ELSE 'Manual review'
  END AS likely_reporting_opportunity
FROM matches m
GROUP BY
  m.theme,
  m.table_name
ORDER BY
  m.theme,
  signal_count DESC,
  m.table_name;

PROMPT ============================================================
PROMPT 4. FORMAL FK MAP BETWEEN F1/W1/X1 AND CORE CI/D1/C1 TABLES
PROMPT ============================================================

SELECT
  c.owner AS child_owner,
  c.table_name AS child_table_name,
  c.constraint_name AS fk_name,
  cc.position AS column_position,
  cc.column_name AS child_column_name,
  p.owner AS parent_owner,
  p.table_name AS parent_table_name,
  pc.column_name AS parent_column_name,
  c.delete_rule
FROM all_constraints c
JOIN all_constraints p
  ON p.owner = c.r_owner
 AND p.constraint_name = c.r_constraint_name
JOIN all_cons_columns cc
  ON cc.owner = c.owner
 AND cc.constraint_name = c.constraint_name
JOIN all_cons_columns pc
  ON pc.owner = p.owner
 AND pc.constraint_name = p.constraint_name
 AND pc.position = cc.position
WHERE c.owner = UPPER('&schema_owner')
  AND c.constraint_type = 'R'
  AND (
        REGEXP_LIKE(c.table_name, '^(F1|W1|X1)_')
     OR REGEXP_LIKE(p.table_name, '^(F1|W1|X1)_')
      )
  AND (
        REGEXP_LIKE(c.table_name, '^(F1|W1|X1|CI|D1|C1)_')
    AND REGEXP_LIKE(p.table_name, '^(F1|W1|X1|CI|D1|C1)_')
      )
ORDER BY
  c.table_name,
  c.constraint_name,
  cc.position;

PROMPT ============================================================
PROMPT 5. NATURAL JOIN CANDIDATES BACK TO CI/D1/C1 WHEN NO FORMAL FK EXISTS
PROMPT ============================================================

WITH prefix_cols AS (
  SELECT
    c.table_name,
    c.column_name
  FROM all_tab_columns c
  WHERE c.owner = UPPER('&schema_owner')
    AND REGEXP_LIKE(c.table_name, '^(F1|W1|X1)_')
    AND REGEXP_LIKE(
          c.column_name,
          '^(ACCT_ID|SA_ID|SP_ID|D1_SP_ID|PREM_ID|PER_ID|BILL_ID|BSEG_ID|FT_ID|PAY_EVENT_ID|PAY_ID|ASSET_ID|D1_DVC_ID|DEVICE_CONFIG_ID|WO_|TSK_ID)'
        )
),
core_cols AS (
  SELECT
    c.table_name,
    c.column_name
  FROM all_tab_columns c
  WHERE c.owner = UPPER('&schema_owner')
    AND REGEXP_LIKE(c.table_name, '^(CI|D1|C1)_')
    AND REGEXP_LIKE(
          c.column_name,
          '^(ACCT_ID|SA_ID|SP_ID|D1_SP_ID|PREM_ID|PER_ID|BILL_ID|BSEG_ID|FT_ID|PAY_EVENT_ID|PAY_ID|ASSET_ID|D1_DVC_ID|DEVICE_CONFIG_ID|WO_|TSK_ID)'
        )
)
SELECT
  p.table_name AS prefix_table_name,
  p.column_name AS join_column_name,
  c.table_name AS core_table_name
FROM prefix_cols p
JOIN core_cols c
  ON c.column_name = p.column_name
ORDER BY
  p.table_name,
  p.column_name,
  c.table_name;

PROMPT ============================================================
PROMPT 6. TOP REPORTING CANDIDATES: COMBINED ROLE + THEME VIEW
PROMPT ============================================================

WITH target_objects AS (
  SELECT
    o.owner,
    o.object_name AS table_name,
    o.object_type
  FROM all_objects o
  WHERE o.owner = UPPER('&schema_owner')
    AND o.object_type IN ('TABLE', 'VIEW', 'MATERIALIZED VIEW')
    AND REGEXP_LIKE(o.object_name, '^(F1|W1|X1)_')
),
profile AS (
  SELECT
    c.table_name,
    SUM(CASE WHEN REGEXP_LIKE(c.column_name, '(AMT|AMOUNT|QTY|QUANTITY|COUNT|CNT|COST|PRICE|TOTAL|HOURS|DURATION)') THEN 1 ELSE 0 END) AS metric_col_count,
    SUM(CASE WHEN REGEXP_LIKE(c.column_name, '(_DT$|_DATE$|_DTTM$|_TS$|_TMSTMP$|_START_|_END_|_CRE_|_UPD_)') THEN 1 ELSE 0 END) AS temporal_col_count,
    SUM(CASE WHEN REGEXP_LIKE(c.column_name, '(STATUS|STAT|_FLG$|_SW$|STATE|RESULT|OUTCOME)') THEN 1 ELSE 0 END) AS status_col_count,
    SUM(CASE WHEN REGEXP_LIKE(c.column_name, '(DESCR|DESCRIPTION|NAME|LONG_NAME|SHORT_NAME)') THEN 1 ELSE 0 END) AS descriptive_col_count
  FROM all_tab_columns c
  WHERE c.owner = UPPER('&schema_owner')
    AND REGEXP_LIKE(c.table_name, '^(F1|W1|X1)_')
  GROUP BY c.table_name
),
themes AS (
  SELECT 'ASSET_LIFECYCLE' AS theme, 'ASSET' AS pattern FROM dual UNION ALL
  SELECT 'ASSET_LIFECYCLE', 'INSTALL' FROM dual UNION ALL
  SELECT 'WORK_EXECUTION', 'WORK' FROM dual UNION ALL
  SELECT 'WORK_EXECUTION', 'TASK' FROM dual UNION ALL
  SELECT 'WORK_EXECUTION', 'TSK' FROM dual UNION ALL
  SELECT 'INVENTORY_MATERIALS', 'ITEM' FROM dual UNION ALL
  SELECT 'INVENTORY_MATERIALS', 'INVENT' FROM dual UNION ALL
  SELECT 'PURCHASING_PROCUREMENT', 'PO_' FROM dual UNION ALL
  SELECT 'PURCHASING_PROCUREMENT', 'VENDOR' FROM dual UNION ALL
  SELECT 'COSTS_AND_FINANCE', 'COST' FROM dual UNION ALL
  SELECT 'COSTS_AND_FINANCE', 'AMT' FROM dual UNION ALL
  SELECT 'APPROVAL_AND_GOVERNANCE', 'APPROV' FROM dual UNION ALL
  SELECT 'METER_DEVICE_LINKAGE', 'DEVICE' FROM dual UNION ALL
  SELECT 'METER_DEVICE_LINKAGE', 'METER' FROM dual UNION ALL
  SELECT 'DEPLOYMENT_AND_INTEGRATION', 'MIGR' FROM dual UNION ALL
  SELECT 'DEPLOYMENT_AND_INTEGRATION', 'BNDL' FROM dual
),
theme_scores AS (
  SELECT
    x.table_name,
    x.theme,
    x.signal_count,
    ROW_NUMBER() OVER (
      PARTITION BY x.table_name
      ORDER BY
        x.signal_count DESC,
        x.theme
    ) AS rn
  FROM (
    SELECT
      c.table_name,
      th.theme,
      COUNT(*) AS signal_count
    FROM all_tab_columns c
    JOIN themes th
      ON UPPER(c.column_name) LIKE '%' || th.pattern || '%'
    WHERE c.owner = UPPER('&schema_owner')
      AND REGEXP_LIKE(c.table_name, '^(F1|W1|X1)_')
    GROUP BY
      c.table_name,
      th.theme
  ) x
)
SELECT
  o.table_name,
  o.object_type,
  CASE
    WHEN REGEXP_LIKE(o.table_name, '(_L$|LOOKUP|TYPE|STATUS)') THEN 'LOOKUP_DIM'
    WHEN p.metric_col_count > 0 AND p.temporal_col_count > 0 THEN 'FACT'
    WHEN p.temporal_col_count > 0 AND p.status_col_count > 0 THEN 'PROCESS_EVENT'
    ELSE 'CONFIG_OR_BRIDGE'
  END AS likely_role,
  ts.theme AS top_theme,
  ts.signal_count AS top_theme_signal_count,
  CASE ts.theme
    WHEN 'ASSET_LIFECYCLE' THEN 'Candidate dashboards: asset inventory, install/remove history, maintenance aging'
    WHEN 'WORK_EXECUTION' THEN 'Candidate dashboards: backlog, assignment, completion SLA, open work aging'
    WHEN 'INVENTORY_MATERIALS' THEN 'Candidate dashboards: stock position, parts usage, issue/receipt exceptions'
    WHEN 'PURCHASING_PROCUREMENT' THEN 'Candidate dashboards: PO pipeline, vendor performance, receipt lag'
    WHEN 'COSTS_AND_FINANCE' THEN 'Candidate dashboards: asset spend, work-order cost rollups, budget vs actual'
    WHEN 'APPROVAL_AND_GOVERNANCE' THEN 'Candidate dashboards: approvals, exception aging, governance audit'
    WHEN 'METER_DEVICE_LINKAGE' THEN 'Candidate dashboards: meter-to-asset linkage, install lineage, device health'
    WHEN 'DEPLOYMENT_AND_INTEGRATION' THEN 'Candidate dashboards: migration run status, interface exceptions, bundle audit'
    ELSE 'Manual review'
  END AS suggested_reporting_opportunity
FROM target_objects o
LEFT JOIN profile p
  ON p.table_name = o.table_name
LEFT JOIN theme_scores ts
  ON ts.table_name = o.table_name
 AND ts.rn = 1
ORDER BY
  likely_role,
  ts.signal_count DESC NULLS LAST,
  o.table_name;

PROMPT ============================================================
PROMPT 7. OPTIONAL DYNAMIC PROFILE: ACTUAL ROW COUNTS + PREFERRED DATE RANGE
PROMPT ============================================================
PROMPT Output is printed through DBMS_OUTPUT.
PROMPT If this is too heavy, lower profile_table_limit before running.

SET SERVEROUTPUT ON SIZE UNLIMITED

DECLARE
  l_count NUMBER;
  l_min_dt VARCHAR2(30);
  l_max_dt VARCHAR2(30);
  l_sql VARCHAR2(4000);
BEGIN
  dbms_output.put_line('TABLE_NAME|TIME_COLUMN|ROW_COUNT|MIN_TIME|MAX_TIME');

  FOR r IN (
    WITH target_tables AS (
      SELECT
        t.table_name,
        t.num_rows
      FROM all_tables t
      WHERE t.owner = UPPER('&schema_owner')
        AND REGEXP_LIKE(t.table_name, '^(F1|W1|X1)_')
    ),
    temporal_candidates AS (
      SELECT
        c.table_name,
        c.column_name,
        ROW_NUMBER() OVER (
          PARTITION BY c.table_name
          ORDER BY
            CASE
              WHEN c.column_name = 'CRE_DTTM' THEN 1
              WHEN c.column_name = 'UPD_DTTM' THEN 2
              WHEN c.column_name = 'START_DTTM' THEN 3
              WHEN c.column_name = 'END_DTTM' THEN 4
              WHEN c.column_name LIKE '%\_DTTM' ESCAPE '\' THEN 5
              WHEN c.column_name LIKE '%\_DT' ESCAPE '\' THEN 6
              WHEN c.column_name LIKE '%DATE%' THEN 7
              ELSE 99
            END,
            c.column_name
        ) AS rn
      FROM all_tab_columns c
      WHERE c.owner = UPPER('&schema_owner')
        AND REGEXP_LIKE(c.table_name, '^(F1|W1|X1)_')
        AND c.data_type IN ('DATE', 'TIMESTAMP', 'TIMESTAMP(6)', 'TIMESTAMP WITH TIME ZONE', 'TIMESTAMP WITH LOCAL TIME ZONE')
    )
    SELECT
      t.table_name,
      tc.column_name AS time_column
    FROM target_tables t
    LEFT JOIN temporal_candidates tc
      ON tc.table_name = t.table_name
     AND tc.rn = 1
    ORDER BY
      t.num_rows DESC NULLS LAST,
      t.table_name
    FETCH FIRST &profile_table_limit ROWS ONLY
  ) LOOP
    IF r.time_column IS NOT NULL THEN
      l_sql :=
        'select count(*), ' ||
        'to_char(min(' || r.time_column || '), ''YYYY-MM-DD HH24:MI:SS''), ' ||
        'to_char(max(' || r.time_column || '), ''YYYY-MM-DD HH24:MI:SS'') ' ||
        'from ' || UPPER('&schema_owner') || '.' || r.table_name;
      EXECUTE IMMEDIATE l_sql INTO l_count, l_min_dt, l_max_dt;
      dbms_output.put_line(
        r.table_name || '|' || r.time_column || '|' || l_count || '|' ||
        NVL(l_min_dt, 'NULL') || '|' || NVL(l_max_dt, 'NULL')
      );
    ELSE
      l_sql := 'select count(*) from ' || UPPER('&schema_owner') || '.' || r.table_name;
      EXECUTE IMMEDIATE l_sql INTO l_count;
      dbms_output.put_line(
        r.table_name || '|(no_time_column)|' || l_count || '|NULL|NULL'
      );
    END IF;
  END LOOP;
END;
/
