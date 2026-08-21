PROMPT ============================================================
PROMPT CISADM DDL helper for limited-privilege deploy accounts
PROMPT (CREATE ANY PROCEDURE + EXECUTE ANY PROCEDURE)
PROMPT ============================================================

CREATE OR REPLACE PROCEDURE cisadm.originba_ddl_helper(
    p_sql IN VARCHAR2
) AUTHID DEFINER AS
BEGIN
    EXECUTE IMMEDIATE p_sql;
END;
/

PROMPT originba_ddl_helper ready.
