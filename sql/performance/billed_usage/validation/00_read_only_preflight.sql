-- 00_read_only_preflight.sql
-- Read-only preflight gate:
-- - prints session user/schema
-- - fails if session has DML/DDL privileges that violate read-only policy

set pagesize 50000
set linesize 220
set trimspool on

SELECT
  USER AS session_user,
  SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA') AS current_schema,
  SYS_CONTEXT('USERENV', 'SESSION_USER') AS session_user_ctx
FROM dual;

WITH risky_privs AS (
  SELECT privilege
  FROM SESSION_PRIVS
  WHERE privilege IN (
    'INSERT ANY TABLE',
    'UPDATE ANY TABLE',
    'DELETE ANY TABLE',
    'CREATE ANY TABLE',
    'ALTER ANY TABLE',
    'DROP ANY TABLE'
  )
  UNION ALL
  SELECT privilege
  FROM USER_TAB_PRIVS_RECD
  WHERE privilege IN ('INSERT', 'UPDATE', 'DELETE', 'ALTER', 'INDEX')
)
SELECT
  'READ_ONLY_PRIVILEGE_GATE' AS gate_name,
  CASE WHEN COUNT(*) = 0 THEN 'PASS' ELSE 'FAIL' END AS gate_status,
  COUNT(*) AS risky_privilege_count
FROM risky_privs;

WITH risky_privs AS (
  SELECT privilege
  FROM SESSION_PRIVS
  WHERE privilege IN (
    'INSERT ANY TABLE',
    'UPDATE ANY TABLE',
    'DELETE ANY TABLE',
    'CREATE ANY TABLE',
    'ALTER ANY TABLE',
    'DROP ANY TABLE'
  )
  UNION ALL
  SELECT privilege
  FROM USER_TAB_PRIVS_RECD
  WHERE privilege IN ('INSERT', 'UPDATE', 'DELETE', 'ALTER', 'INDEX')
)
SELECT 1 / CASE WHEN COUNT(*) = 0 THEN 1 ELSE 0 END AS assert_read_only_privileges
FROM risky_privs;
