BEGIN
    EXECUTE IMMEDIATE '
        ALTER TABLE cisadm.ft_gl_distribution_rpt_curr
        ADD (
            batch_cd            VARCHAR2(30),
            batch_nbr           NUMBER(18,0),
            is_latest_batch_nbr VARCHAR2(5)
        )';
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE != -1430 THEN
            RAISE;
        END IF;
END;
/

BEGIN
    EXECUTE IMMEDIATE '
        ALTER TABLE cisadm.ft_gl_distribution_rpt_curr
        ADD (
            debit_amt  NUMBER(15,2),
            credit_amt NUMBER(15,2)
        )';
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE != -1430 THEN
            RAISE;
        END IF;
END;
/
