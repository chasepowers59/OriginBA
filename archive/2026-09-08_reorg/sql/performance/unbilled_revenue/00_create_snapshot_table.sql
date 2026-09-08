-- Purpose:
--   One-time DDL for unbilled revenue daily snapshot.
--   Table is partitioned by AS_OF_DT for fast incremental loads and retention management.
--
-- Notes:
--   - Run once in CISADM (or approved reporting schema).
--   - If object exists already, adjust manually instead of rerunning blindly.

CREATE TABLE CISADM.C1_BI_UNBILLED_REV_SNAP (
  AS_OF_DT                 DATE            NOT NULL,
  ACCT_ID                  CHAR(40)        NOT NULL,
  SA_ID                    CHAR(40)        NOT NULL,
  CIS_DIVISION             CHAR(20),
  SA_TYPE_CD               CHAR(32),
  SA_TYPE_DESCR            VARCHAR2(240),
  BILL_CYC_CD              CHAR(16),
  BILL_CYC_DESCR           VARCHAR2(240),
  CUST_CL_CD               CHAR(32),
  CUST_CLASS_DESCR         VARCHAR2(240),
  COLL_CL_CD               CHAR(40),
  COLL_CLASS_DESCR         VARCHAR2(240),
  RATE_SCHEDULE_CD         CHAR(32),
  RATE_SCHEDULE_DESCR      VARCHAR2(240),
  LAST_BSEG_END_DT         DATE,
  LAST_BILL_ACCOUNTING_DT  DATE,
  UNBILLED_DAYS            NUMBER(10,0),
  UNBILLED_USAGE_QTY       NUMBER(22,6),
  EST_USAGE_AMT            NUMBER(22,6),
  EST_OTHER_AMT            NUMBER(22,6),
  EST_TAX_RATE             NUMBER(22,12),
  EST_TAX_AMT              NUMBER(22,6),
  EST_TOTAL_AMT            NUMBER(22,6),
  CALC_METHOD_CD           VARCHAR2(64),
  LOAD_DTTM                DATE            DEFAULT SYSDATE NOT NULL,
  CONSTRAINT C1_BI_UNBILLED_REV_SNAP_PK PRIMARY KEY (AS_OF_DT, SA_ID)
)
PARTITION BY RANGE (AS_OF_DT)
INTERVAL (NUMTOYMINTERVAL(1, 'MONTH'))
(
  PARTITION P202509 VALUES LESS THAN (DATE '2025-10-01')
)
COMPRESS FOR QUERY HIGH;

CREATE INDEX CISADM.C1BI_UBR_ACCT_DT_X1
  ON CISADM.C1_BI_UNBILLED_REV_SNAP (ACCT_ID, AS_OF_DT);

CREATE INDEX CISADM.C1BI_UBR_CLASS_DT_X2
  ON CISADM.C1_BI_UNBILLED_REV_SNAP (BILL_CYC_CD, CUST_CL_CD, AS_OF_DT);

CREATE INDEX CISADM.C1BI_UBR_RS_DT_X3
  ON CISADM.C1_BI_UNBILLED_REV_SNAP (RATE_SCHEDULE_CD, AS_OF_DT);
