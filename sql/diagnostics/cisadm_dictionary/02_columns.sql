-- 02_columns.sql
-- Read-only column-level metadata for a schema owner.
-- Expected define variable:
--   schema_owner = CISADM

SELECT
  c.owner,
  c.table_name,
  tc.comments AS table_comment,
  c.column_id,
  c.column_name,
  cc.comments AS column_comment,
  c.data_type,
  c.data_length,
  c.data_precision,
  c.data_scale,
  c.nullable,
  c.char_length,
  c.char_used
FROM ALL_TAB_COLUMNS c
LEFT JOIN ALL_COL_COMMENTS cc
  ON cc.owner = c.owner
 AND cc.table_name = c.table_name
 AND cc.column_name = c.column_name
LEFT JOIN ALL_TAB_COMMENTS tc
  ON tc.owner = c.owner
 AND tc.table_name = c.table_name
WHERE c.owner = UPPER('&schema_owner')
ORDER BY c.table_name, c.column_id;
