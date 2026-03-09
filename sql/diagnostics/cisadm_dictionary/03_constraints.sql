-- 03_constraints.sql
-- Read-only constraint metadata for a schema owner.
-- Expected define variable:
--   schema_owner = CISADM

SELECT
  c.owner,
  c.table_name,
  c.constraint_name,
  c.constraint_type,
  c.status,
  c.validated,
  c.deferrable,
  c.deferred,
  c.delete_rule,
  c.r_owner AS referenced_owner,
  rc.table_name AS referenced_table_name,
  c.search_condition_vc
FROM ALL_CONSTRAINTS c
LEFT JOIN ALL_CONSTRAINTS rc
  ON rc.owner = c.r_owner
 AND rc.constraint_name = c.r_constraint_name
WHERE c.owner = UPPER('&schema_owner')
ORDER BY c.table_name, c.constraint_name;
