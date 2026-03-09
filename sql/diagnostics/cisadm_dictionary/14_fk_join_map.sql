-- 14_fk_join_map.sql
-- Read-only FK join map with child/parent columns.
-- Expected define variable:
--   schema_owner = CISADM

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
FROM ALL_CONSTRAINTS c
JOIN ALL_CONSTRAINTS p
  ON p.owner = c.r_owner
 AND p.constraint_name = c.r_constraint_name
JOIN ALL_CONS_COLUMNS cc
  ON cc.owner = c.owner
 AND cc.constraint_name = c.constraint_name
JOIN ALL_CONS_COLUMNS pc
  ON pc.owner = p.owner
 AND pc.constraint_name = p.constraint_name
 AND pc.position = cc.position
WHERE c.owner = UPPER('&schema_owner')
  AND c.constraint_type = 'R'
ORDER BY c.table_name, c.constraint_name, cc.position;

