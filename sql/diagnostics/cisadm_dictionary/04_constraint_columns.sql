-- 04_constraint_columns.sql
-- Read-only constraint column metadata for a schema owner.
-- Expected define variable:
--   schema_owner = CISADM

SELECT
  c.owner,
  c.table_name,
  c.constraint_name,
  c.constraint_type,
  cc.position,
  cc.column_name
FROM ALL_CONSTRAINTS c
JOIN ALL_CONS_COLUMNS cc
  ON cc.owner = c.owner
 AND cc.constraint_name = c.constraint_name
WHERE c.owner = UPPER('&schema_owner')
ORDER BY c.table_name, c.constraint_name, cc.position;
