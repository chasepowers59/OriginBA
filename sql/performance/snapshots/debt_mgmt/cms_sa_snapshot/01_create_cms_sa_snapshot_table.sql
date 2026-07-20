-- Legacy CMS SA aged-balance snapshot expected by Standard Offering
-- Debt Management domain: SA Snapshot - Aged Balance.
-- Domain physical table: CISADM.CMS_SA_SNAPSHOT (schemaAlias CISADM).
-- Domain derived query CMS_ACCT_SNAPSHOT rolls this table up by ACCT_ID.

PROMPT ============================================================
PROMPT Create CISADM.CMS_SA_SNAPSHOT (CityCorp / Standard Offering)
PROMPT ============================================================

BEGIN
    EXECUTE IMMEDIATE 'DROP TABLE cisadm.cms_sa_snapshot CASCADE CONSTRAINTS';
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE != -942 THEN
            RAISE;
        END IF;
END;
/

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
);

ALTER TABLE cisadm.cms_sa_snapshot
    ADD CONSTRAINT pk_cms_sa_snapshot
    PRIMARY KEY (sa_id, c1_snapshot_dt, cm_snapshot_type_flg);

CREATE INDEX cisadm.ix_cms_sa_snapshot_acct
    ON cisadm.cms_sa_snapshot (acct_id, c1_snapshot_dt, cm_snapshot_type_flg);

CREATE INDEX cisadm.ix_cms_sa_snapshot_dt
    ON cisadm.cms_sa_snapshot (c1_snapshot_dt, cm_snapshot_type_flg);

GRANT SELECT ON cisadm.cms_sa_snapshot TO cis_read;
GRANT SELECT, INSERT, UPDATE, DELETE ON cisadm.cms_sa_snapshot TO cis_user;
GRANT SELECT ON cisadm.cms_sa_snapshot TO cisread;
GRANT SELECT ON cisadm.cms_sa_snapshot TO cisuser;
GRANT SELECT ON cisadm.cms_sa_snapshot TO jrs2c2m;

-- Fix invalid CISREAD synonym that previously pointed at missing CISADM object.
CREATE OR REPLACE SYNONYM cisread.cms_sa_snapshot FOR cisadm.cms_sa_snapshot;

PROMPT CMS_SA_SNAPSHOT table created.
