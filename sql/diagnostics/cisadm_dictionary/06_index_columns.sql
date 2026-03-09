-- 06_index_columns.sql
-- Read-only index column metadata for a schema owner.
-- Expected define variable:
--   schema_owner = CISADM

SELECT
  ic.index_owner,
  ic.table_name,
  ic.index_name,
  ic.column_position,
  ic.column_name,
  ic.descend
FROM ALL_IND_COLUMNS ic
WHERE ic.table_owner = UPPER('&schema_owner')
ORDER BY ic.table_name, ic.index_name, ic.column_position;
