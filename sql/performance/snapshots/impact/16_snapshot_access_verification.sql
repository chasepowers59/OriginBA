-- Purpose:
--   Verify the current Oracle session is appropriate for read-only diagnostics
--   before running snapshot analysis or runtime capture.
--
-- Use this when:
--   - first connecting through VPN
--   - confirming whether the current account is read-only
--   - documenting roles and grants available to the session

PROMPT ============================================================================
PROMPT 16a. Current session identity
PROMPT ============================================================================

SELECT
    SYS_CONTEXT('USERENV', 'SESSION_USER') AS session_user,
    SYS_CONTEXT('USERENV', 'CURRENT_SCHEMA') AS current_schema,
    SYS_CONTEXT('USERENV', 'DB_NAME') AS db_name,
    SYS_CONTEXT('USERENV', 'SERVICE_NAME') AS service_name,
    SYSTIMESTAMP AS current_timestamp
FROM dual;

PROMPT
PROMPT ============================================================================
PROMPT 16b. Enabled session roles
PROMPT ============================================================================

SELECT role
FROM session_roles
ORDER BY role;

PROMPT
PROMPT ============================================================================
PROMPT 16c. Direct system privileges for the current user
PROMPT ============================================================================

SELECT privilege
FROM user_sys_privs
ORDER BY privilege;

PROMPT
PROMPT ============================================================================
PROMPT 16d. Table privileges granted directly to the current user
PROMPT ============================================================================

SELECT
    owner,
    table_name,
    privilege
FROM all_tab_privs
WHERE grantee = SYS_CONTEXT('USERENV', 'SESSION_USER')
ORDER BY owner, table_name, privilege;

PROMPT
PROMPT ============================================================================
PROMPT 16e. High-risk privileges quick check
PROMPT ============================================================================

SELECT
    CASE
        WHEN EXISTS (
            SELECT 1
            FROM user_sys_privs
            WHERE privilege IN (
                'CREATE ANY TABLE',
                'ALTER ANY TABLE',
                'DROP ANY TABLE',
                'INSERT ANY TABLE',
                'UPDATE ANY TABLE',
                'DELETE ANY TABLE',
                'EXECUTE ANY PROCEDURE'
            )
        )
        THEN 'YES'
        ELSE 'NO'
    END AS has_high_risk_system_privs
FROM dual;

PROMPT
PROMPT ============================================================================
PROMPT 16f. Snapshot-table object privileges visible to the current user
PROMPT ============================================================================

SELECT
    owner,
    table_name,
    privilege
FROM all_tab_privs
WHERE grantee = SYS_CONTEXT('USERENV', 'SESSION_USER')
  AND owner = 'CISADM'
  AND table_name IN (
      'FT_RPT_CURR',
      'BSEG_BILLED_USAGE_RPT_CURR',
      'BSEG_SQ_USAGE_RPT_CURR',
      'D1_MSRMT_RPT_CURR',
      'FT_GL_DISTRIBUTION_RPT_CURR',
      'D1_USAGE_RPT_CURR',
      'D1_USAGE_SCALAR_DTL_RPT_CURR'
  )
ORDER BY table_name, privilege;
