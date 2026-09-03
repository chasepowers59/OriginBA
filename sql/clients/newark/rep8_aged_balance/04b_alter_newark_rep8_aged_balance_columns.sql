-- Add credit-balance / customer-status / comments columns.
-- Uses originba_ddl_helper2 (CPOWERS cannot ALTER CISADM tables directly).
-- Safe to re-run (ignores ORA-01430 column already exists).

PROMPT Altering CISADM.NEWARK_REP8_AGED_BALANCE via originba_ddl_helper2...

DECLARE
    PROCEDURE add_col(p_ddl VARCHAR2) IS
    BEGIN
        cisadm.originba_ddl_helper2(p_ddl);
    EXCEPTION
        WHEN OTHERS THEN
            IF SQLCODE NOT IN (-1430) THEN
                RAISE;
            END IF;
    END;
BEGIN
    -- prior extension (idempotent)
    add_col('ALTER TABLE cisadm.newark_rep8_aged_balance ADD (coll_cl_cd VARCHAR2(30))');
    add_col('ALTER TABLE cisadm.newark_rep8_aged_balance ADD (coll_cl_desc VARCHAR2(100))');
    add_col('ALTER TABLE cisadm.newark_rep8_aged_balance ADD (cust_cl_cd VARCHAR2(30))');
    add_col('ALTER TABLE cisadm.newark_rep8_aged_balance ADD (cust_cl_desc VARCHAR2(100))');
    add_col('ALTER TABLE cisadm.newark_rep8_aged_balance ADD (cis_division VARCHAR2(10))');
    add_col('ALTER TABLE cisadm.newark_rep8_aged_balance ADD (prem_id CHAR(10))');
    add_col('ALTER TABLE cisadm.newark_rep8_aged_balance ADD (service_address_zip_code VARCHAR2(12))');
    add_col('ALTER TABLE cisadm.newark_rep8_aged_balance ADD (has_active_sa CHAR(1))');
    add_col('ALTER TABLE cisadm.newark_rep8_aged_balance ADD (active_sa_count NUMBER(10,0))');
    add_col('ALTER TABLE cisadm.newark_rep8_aged_balance ADD (inactive_only_sw CHAR(1))');
    add_col('ALTER TABLE cisadm.newark_rep8_aged_balance ADD (sa_status_summary VARCHAR2(20))');

    -- customer status (legacy STATUS) + property type
    add_col('ALTER TABLE cisadm.newark_rep8_aged_balance ADD (customer_status_cd VARCHAR2(30))');
    add_col('ALTER TABLE cisadm.newark_rep8_aged_balance ADD (customer_status_desc VARCHAR2(100))');
    add_col('ALTER TABLE cisadm.newark_rep8_aged_balance ADD (customer_status_all VARCHAR2(500))');
    add_col('ALTER TABLE cisadm.newark_rep8_aged_balance ADD (property_type_cd VARCHAR2(50))');
    add_col('ALTER TABLE cisadm.newark_rep8_aged_balance ADD (property_type_desc VARCHAR2(100))');

    -- credit balance flag + comments
    add_col('ALTER TABLE cisadm.newark_rep8_aged_balance ADD (has_credit_balance CHAR(1))');
    add_col('ALTER TABLE cisadm.newark_rep8_aged_balance ADD (comments VARCHAR2(2000))');

    -- widen legacy STATUS for customer-status descriptions
    BEGIN
        cisadm.originba_ddl_helper2(
            'ALTER TABLE cisadm.newark_rep8_aged_balance MODIFY (status VARCHAR2(100))'
        );
    EXCEPTION
        WHEN OTHERS THEN
            NULL;
    END;
END;
/

PROMPT Alter complete — recreate demographics view, refresh proc, and JRS2C2M views.
