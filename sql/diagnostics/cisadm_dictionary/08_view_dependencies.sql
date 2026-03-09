-- 08_view_dependencies.sql
-- Read-only dependencies for views in a schema owner.
-- Expected define variable:
--   schema_owner = CISADM

SELECT
  d.owner AS view_owner,
  d.name AS view_name,
  d.referenced_owner,
  d.referenced_name,
  d.referenced_type
FROM ALL_DEPENDENCIES d
WHERE d.owner = UPPER('&schema_owner')
  AND d.type = 'VIEW'
ORDER BY d.name, d.referenced_owner, d.referenced_name;

