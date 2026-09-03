-- Grants for Newark REP8 staging (via CISADM.originba_ddl_helper2).

PROMPT Applying Newark REP8 grants via originba_ddl_helper2...

BEGIN
    cisadm.originba_ddl_helper2(
        'GRANT SELECT ON cisadm.newark_rep8_aged_balance TO cis_read'
    );
    cisadm.originba_ddl_helper2(
        'GRANT SELECT, INSERT, UPDATE, DELETE ON cisadm.newark_rep8_aged_balance TO cis_user'
    );
    cisadm.originba_ddl_helper2(
        'GRANT SELECT ON cisadm.newark_rep8_aged_balance TO cisread'
    );
    cisadm.originba_ddl_helper2(
        'GRANT SELECT ON cisadm.newark_rep8_aged_balance TO cisuser'
    );
    cisadm.originba_ddl_helper2(
        'GRANT SELECT ON cisadm.newark_rep8_aged_balance TO jrs2c2m'
    );
    cisadm.originba_ddl_helper2(
        'GRANT EXECUTE ON cisadm.refresh_newark_rep8_aged_balance TO jrs2c2m'
    );
END;
/

PROMPT Newark REP8 grants applied.
