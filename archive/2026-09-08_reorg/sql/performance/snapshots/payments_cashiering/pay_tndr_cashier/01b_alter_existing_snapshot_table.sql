BEGIN
    EXECUTE IMMEDIATE '
        ALTER TABLE cisadm.pay_tndr_cash_rpt_curr
        ADD (
            source_family_cd   VARCHAR2(32),
            source_family_desc VARCHAR2(120)
        )';
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE != -1430 THEN
            RAISE;
        END IF;
END;
/
