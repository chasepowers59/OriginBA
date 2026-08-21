PROMPT ============================================================
PROMPT Post-load snapshot indexes (limited-priv via ORIGINBA_DDL_HELPER2)
PROMPT Prefer after full-history baseline so CREATE INDEX scans loaded data once.
PROMPT Idempotent: ignores ORA-00955 (name exists) / ORA-01408 (same columns).
PROMPT ============================================================

-- Helper: create index if missing
-- FT_RPT_CURR — Ad Hoc / report filter pattern (matches Ellensburg)
BEGIN
    cisadm.originba_ddl_helper2(
        'CREATE INDEX cisadm.xoba_ftrpt_ft_acctdt ON cisadm.ft_rpt_curr (ft_type_flg, accounting_dt)'
    );
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE NOT IN (-955, -1408) THEN RAISE; END IF;
END;
/

BEGIN
    cisadm.originba_ddl_helper2(
        'CREATE INDEX cisadm.xoba_ftrpt_acct_dt ON cisadm.ft_rpt_curr (acct_id, accounting_dt)'
    );
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE NOT IN (-955, -1408) THEN RAISE; END IF;
END;
/

BEGIN
    cisadm.originba_ddl_helper2(
        'CREATE UNIQUE INDEX cisadm.xoba_ftrpt_pk ON cisadm.ft_rpt_curr (ft_id)'
    );
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE NOT IN (-955, -1408, -1452) THEN RAISE; END IF;
END;
/

-- FT_GL_DISTRIBUTION_RPT_CURR — checklist primary + Ellensburg-style adj path
BEGIN
    cisadm.originba_ddl_helper2(
        'CREATE INDEX cisadm.xoba_ftglrpt_ft_dst_acctdt ON cisadm.ft_gl_distribution_rpt_curr (ft_type_flg, dst_id, accounting_dt)'
    );
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE NOT IN (-955, -1408) THEN RAISE; END IF;
END;
/

BEGIN
    cisadm.originba_ddl_helper2(
        'CREATE INDEX cisadm.xoba_ftglrpt_ft_adjstat_acctdt ON cisadm.ft_gl_distribution_rpt_curr (ft_type_flg, adj_status_flg, accounting_dt)'
    );
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE NOT IN (-955, -1408) THEN RAISE; END IF;
END;
/

BEGIN
    cisadm.originba_ddl_helper2(
        'CREATE UNIQUE INDEX cisadm.xoba_ftglrpt_pk ON cisadm.ft_gl_distribution_rpt_curr (ft_id, gl_seq_nbr)'
    );
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE NOT IN (-955, -1408, -1452) THEN RAISE; END IF;
END;
/

-- BSEG_BILLED_USAGE_RPT_CURR
BEGIN
    cisadm.originba_ddl_helper2(
        'CREATE UNIQUE INDEX cisadm.xoba_bsegbill_pk ON cisadm.bseg_billed_usage_rpt_curr (bseg_id)'
    );
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE NOT IN (-955, -1408, -1452) THEN RAISE; END IF;
END;
/

BEGIN
    cisadm.originba_ddl_helper2(
        'CREATE INDEX cisadm.xoba_bsegbill_acct_billdt ON cisadm.bseg_billed_usage_rpt_curr (acct_id, bill_dt)'
    );
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE NOT IN (-955, -1408) THEN RAISE; END IF;
END;
/

BEGIN
    cisadm.originba_ddl_helper2(
        'CREATE INDEX cisadm.xoba_bsegbill_billdt ON cisadm.bseg_billed_usage_rpt_curr (bill_dt)'
    );
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE NOT IN (-955, -1408) THEN RAISE; END IF;
END;
/

-- BSEG_SQ_USAGE_RPT_CURR (determinant grain — nonunique on bseg_id)
BEGIN
    cisadm.originba_ddl_helper2(
        'CREATE INDEX cisadm.xoba_bsegsq_bseg ON cisadm.bseg_sq_usage_rpt_curr (bseg_id)'
    );
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE NOT IN (-955, -1408) THEN RAISE; END IF;
END;
/

BEGIN
    cisadm.originba_ddl_helper2(
        'CREATE INDEX cisadm.xoba_bsegsq_acct_billdt ON cisadm.bseg_sq_usage_rpt_curr (acct_id, bill_dt)'
    );
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE NOT IN (-955, -1408) THEN RAISE; END IF;
END;
/

BEGIN
    cisadm.originba_ddl_helper2(
        'CREATE INDEX cisadm.xoba_bsegsq_billdt ON cisadm.bseg_sq_usage_rpt_curr (bill_dt)'
    );
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE NOT IN (-955, -1408) THEN RAISE; END IF;
END;
/

-- D1_USAGE_RPT_CURR
BEGIN
    cisadm.originba_ddl_helper2(
        'CREATE UNIQUE INDEX cisadm.xoba_d1usage_pk ON cisadm.d1_usage_rpt_curr (d1_usage_id)'
    );
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE NOT IN (-955, -1408, -1452) THEN RAISE; END IF;
END;
/

BEGIN
    cisadm.originba_ddl_helper2(
        'CREATE INDEX cisadm.xoba_d1usage_end_dttm ON cisadm.d1_usage_rpt_curr (end_dttm)'
    );
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE NOT IN (-955, -1408) THEN RAISE; END IF;
END;
/

BEGIN
    cisadm.originba_ddl_helper2(
        'CREATE INDEX cisadm.xoba_d1usage_acct_end ON cisadm.d1_usage_rpt_curr (acct_id, end_dttm)'
    );
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE NOT IN (-955, -1408) THEN RAISE; END IF;
END;
/

-- D1_USAGE_SCALAR_DTL_RPT_CURR — source can have duplicate (usage,seq); nonunique only
BEGIN
    cisadm.originba_ddl_helper2(
        'CREATE INDEX cisadm.xoba_d1scalar_usage_seq ON cisadm.d1_usage_scalar_dtl_rpt_curr (d1_usage_id, seq_num)'
    );
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE NOT IN (-955, -1408) THEN RAISE; END IF;
END;
/

BEGIN
    cisadm.originba_ddl_helper2(
        'CREATE INDEX cisadm.xoba_d1scalar_end_dttm ON cisadm.d1_usage_scalar_dtl_rpt_curr (usage_end_dttm)'
    );
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE NOT IN (-955, -1408) THEN RAISE; END IF;
END;
/

-- D1_MSRMT_RPT_CURR
BEGIN
    cisadm.originba_ddl_helper2(
        'CREATE UNIQUE INDEX cisadm.xoba_d1msrmt_pk ON cisadm.d1_msrmt_rpt_curr (measr_comp_id, msrmt_dttm)'
    );
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE NOT IN (-955, -1408, -1452) THEN RAISE; END IF;
END;
/

BEGIN
    cisadm.originba_ddl_helper2(
        'CREATE INDEX cisadm.xoba_d1msrmt_dttm ON cisadm.d1_msrmt_rpt_curr (msrmt_dttm)'
    );
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE NOT IN (-955, -1408) THEN RAISE; END IF;
END;
/

-- CMS_SA_SNAPSHOT — align with CityCorp TEST
BEGIN
    cisadm.originba_ddl_helper2(
        'ALTER TABLE cisadm.cms_sa_snapshot ADD CONSTRAINT pk_cms_sa_snapshot PRIMARY KEY (sa_id, c1_snapshot_dt, cm_snapshot_type_flg)'
    );
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE NOT IN (-2260, -955, -2261) THEN RAISE; END IF;
END;
/

BEGIN
    cisadm.originba_ddl_helper2(
        'CREATE INDEX cisadm.ix_cms_sa_snapshot_acct ON cisadm.cms_sa_snapshot (acct_id, c1_snapshot_dt, cm_snapshot_type_flg)'
    );
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE NOT IN (-955, -1408) THEN RAISE; END IF;
END;
/

BEGIN
    cisadm.originba_ddl_helper2(
        'CREATE INDEX cisadm.ix_cms_sa_snapshot_dt ON cisadm.cms_sa_snapshot (c1_snapshot_dt, cm_snapshot_type_flg)'
    );
EXCEPTION
    WHEN OTHERS THEN
        IF SQLCODE NOT IN (-955, -1408) THEN RAISE; END IF;
END;
/

PROMPT Post-load snapshot indexes complete.
SELECT table_name, index_name
FROM all_indexes
WHERE owner = 'CISADM'
  AND table_name IN (
      'FT_RPT_CURR',
      'BSEG_BILLED_USAGE_RPT_CURR',
      'BSEG_SQ_USAGE_RPT_CURR',
      'D1_MSRMT_RPT_CURR',
      'FT_GL_DISTRIBUTION_RPT_CURR',
      'D1_USAGE_RPT_CURR',
      'D1_USAGE_SCALAR_DTL_RPT_CURR',
      'CMS_SA_SNAPSHOT'
  )
ORDER BY 1, 2;
