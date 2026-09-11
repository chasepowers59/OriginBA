-- Newark REP8 nightly staging table (account grain, full REP8_VW row shape).
-- Physical table in CISADM (tablespace quota); JRS2C2M synonym for legacy report RPT_SCHEMA.

PROMPT Creating CISADM.NEWARK_REP8_AGED_BALANCE table...

BEGIN
    EXECUTE IMMEDIATE 'DROP TABLE cisadm.newark_rep8_aged_balance CASCADE CONSTRAINTS';
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE != -942 THEN
            RAISE;
        END IF;
END;
/

CREATE TABLE cisadm.newark_rep8_aged_balance (
    rpt_dt                  DATE            NOT NULL,
    account                 CHAR(10)        NOT NULL,
    lot                     VARCHAR2(50),
    lotsuff                 VARCHAR2(50),
    block                   VARCHAR2(50),
    blocksuf                VARCHAR2(50),
    qlfr                    VARCHAR2(50),
    block_lot               VARCHAR2(100),
    status                  VARCHAR2(100),         -- legacy: Customer Status (CUST STA) description
    customer_status_cd      VARCHAR2(30),
    customer_status_desc    VARCHAR2(100),
    customer_status_all     VARCHAR2(500),
    coll_cl_cd              VARCHAR2(30),
    coll_cl_desc            VARCHAR2(100),
    cust_cl_cd              VARCHAR2(30),
    cust_cl_desc            VARCHAR2(100),
    cis_division            VARCHAR2(10),
    prem_id                 CHAR(10),
    property_descr          VARCHAR2(254),         -- legacy: Property Type (PRPRTYTY)
    property_type_cd        VARCHAR2(50),
    property_type_desc      VARCHAR2(100),
    cycle                   VARCHAR2(30),
    estimated               VARCHAR2(1),
    service_location_name   VARCHAR2(254),         -- primary person entity name
    service_address         VARCHAR2(1000),
    service_address_zip_code VARCHAR2(12),
    service_phone           VARCHAR2(24),
    billing_name            VARCHAR2(254),
    billing_address         VARCHAR2(1000),
    city_state              VARCHAR2(254),
    zip_code                VARCHAR2(12),
    billing_phone           VARCHAR2(24),
    ward                    VARCHAR2(50),
    street_name             VARCHAR2(254),
    current_bal             NUMBER(15,2)    NOT NULL,
    new_charges             NUMBER(15,2)    NOT NULL,
    arrears_30_principal    NUMBER(15,2)    NOT NULL,
    arrears_30_interest     NUMBER(15,2)    NOT NULL,
    arrears_60_principal    NUMBER(15,2)    NOT NULL,
    arrears_60_interest     NUMBER(15,2)    NOT NULL,
    arrears_90_principal    NUMBER(15,2)    NOT NULL,
    arrears_90_interest     NUMBER(15,2)    NOT NULL,
    arrears_total           NUMBER(15,2)    NOT NULL,
    latest_pay_dt           DATE,
    pa_flag                 CHAR(1)         NOT NULL,
    has_active_sa           CHAR(1),
    active_sa_count         NUMBER(10,0),
    inactive_only_sw        CHAR(1),
    sa_status_summary       VARCHAR2(20),
    has_credit_balance      CHAR(1),
    comments                VARCHAR2(2000),
    refreshed_at            TIMESTAMP       DEFAULT SYSTIMESTAMP NOT NULL
);

BEGIN
    EXECUTE IMMEDIATE '
        ALTER TABLE cisadm.newark_rep8_aged_balance
        ADD CONSTRAINT pk_newark_rep8_aged_balance
        PRIMARY KEY (rpt_dt, account)';
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE NOT IN (-2260, -2261, -1031, -2275) THEN
            RAISE;
        END IF;
END;
/

BEGIN
    EXECUTE IMMEDIATE '
        CREATE INDEX cisadm.ix_newark_rep8_ab_acct
        ON cisadm.newark_rep8_aged_balance (account, rpt_dt)';
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE NOT IN (-955, -1031, -1408, -41900) THEN
            RAISE;
        END IF;
END;
/

PROMPT CISADM.NEWARK_REP8_AGED_BALANCE created (run 10_newark_rep8_grants.sql for JRS2C2M access).
