PROMPT Create CMS_SA_SNAPSHOT without DROP/PK/INDEX/GRANT (limited priv)
PROMPT Then apply PK/indexes/grants via originba_ddl_helper2

BEGIN
    EXECUTE IMMEDIATE q'[
CREATE TABLE cisadm.cms_sa_snapshot (
    sa_id                  CHAR(10)        NOT NULL,
    c1_snapshot_dt         DATE            NOT NULL,
    cm_snapshot_type_flg   CHAR(4)         NOT NULL,
    acct_id                CHAR(10)        NOT NULL,
    per_id                 CHAR(10)        NOT NULL,
    currency_cd            CHAR(3)         NOT NULL,
    cur_bal                NUMBER(15,2)    NOT NULL,
    tot_bal                NUMBER(15,2)    NOT NULL,
    new_chg_bal            NUMBER(15,2)    NOT NULL,
    ars_amt1               NUMBER(15,2)    NOT NULL,
    ars_amt2               NUMBER(15,2)    NOT NULL,
    ars_amt3               NUMBER(15,2)    NOT NULL,
    ars_amt4               NUMBER(15,2)    NOT NULL,
    ars_amt5               NUMBER(15,2)    NOT NULL,
    ars_amt6               NUMBER(15,2)    NOT NULL,
    ars_amt7               NUMBER(15,2)    NOT NULL,
    ars_amt8               NUMBER(15,2)    NOT NULL,
    ars_amt9               NUMBER(15,2)    NOT NULL,
    ars_amt10              NUMBER(15,2)    NOT NULL,
    sa_snapshot_cnt        NUMBER          NOT NULL,
    ilm_dt                 DATE,
    ilm_arch_sw            CHAR(1)
)]';
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE NOT IN (-955) THEN
            RAISE;
        END IF;
END;
/

BEGIN
    cisadm.originba_ddl_helper2(q'[ALTER TABLE cisadm.cms_sa_snapshot ADD CONSTRAINT pk_cms_sa_snapshot PRIMARY KEY (sa_id, c1_snapshot_dt, cm_snapshot_type_flg)]');
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE NOT IN (-2260, -955) THEN
            RAISE;
        END IF;
END;
/

BEGIN
    cisadm.originba_ddl_helper2('CREATE INDEX cisadm.ix_cms_sa_snapshot_acct ON cisadm.cms_sa_snapshot (acct_id, c1_snapshot_dt, cm_snapshot_type_flg)');
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE NOT IN (-955) THEN
            RAISE;
        END IF;
END;
/

BEGIN
    cisadm.originba_ddl_helper2('CREATE INDEX cisadm.ix_cms_sa_snapshot_dt ON cisadm.cms_sa_snapshot (c1_snapshot_dt, cm_snapshot_type_flg)');
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE NOT IN (-955) THEN
            RAISE;
        END IF;
END;
/

CREATE OR REPLACE SYNONYM cisread.cms_sa_snapshot FOR cisadm.cms_sa_snapshot;
