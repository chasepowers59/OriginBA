PROMPT ============================================================
PROMPT Apply object grants via CISADM.originba_ddl_helper2 (resilient)
PROMPT Skips missing grantees (ORA-01917) and missing objects (ORA-00942)
PROMPT ============================================================

DECLARE
    PROCEDURE g(p_sql VARCHAR2) IS
    BEGIN
        cisadm.originba_ddl_helper2(p_sql);
    EXCEPTION
        WHEN OTHERS THEN
            IF SQLCODE IN (-1917, -942, -1031) THEN
                NULL; -- missing role/user/object/priv
            ELSE
                RAISE;
            END IF;
    END;
BEGIN
    -- Active 7
    g('GRANT SELECT ON cisadm.ft_rpt_curr TO cis_read');
    g('GRANT SELECT, INSERT, UPDATE, DELETE ON cisadm.ft_rpt_curr TO cis_user');
    g('GRANT SELECT ON cisadm.ft_rpt_curr TO cisread');
    g('GRANT SELECT ON cisadm.ft_rpt_curr TO cisuser');
    g('GRANT SELECT ON cisadm.ft_rpt_curr TO jrs2c2m');

    g('GRANT SELECT ON cisadm.bseg_billed_usage_rpt_curr TO cis_read');
    g('GRANT SELECT, INSERT, UPDATE, DELETE ON cisadm.bseg_billed_usage_rpt_curr TO cis_user');
    g('GRANT SELECT ON cisadm.bseg_billed_usage_rpt_curr TO cisread');
    g('GRANT SELECT ON cisadm.bseg_billed_usage_rpt_curr TO cisuser');
    g('GRANT SELECT ON cisadm.bseg_billed_usage_rpt_curr TO jrs2c2m');

    g('GRANT SELECT ON cisadm.bseg_sq_usage_rpt_curr TO cis_read');
    g('GRANT SELECT, INSERT, UPDATE, DELETE ON cisadm.bseg_sq_usage_rpt_curr TO cis_user');
    g('GRANT SELECT ON cisadm.bseg_sq_usage_rpt_curr TO cisread');
    g('GRANT SELECT ON cisadm.bseg_sq_usage_rpt_curr TO cisuser');
    g('GRANT SELECT ON cisadm.bseg_sq_usage_rpt_curr TO jrs2c2m');

    g('GRANT SELECT ON cisadm.d1_msrmt_rpt_curr TO cis_read');
    g('GRANT SELECT, INSERT, UPDATE, DELETE ON cisadm.d1_msrmt_rpt_curr TO cis_user');
    g('GRANT SELECT ON cisadm.d1_msrmt_rpt_curr TO cisread');
    g('GRANT SELECT ON cisadm.d1_msrmt_rpt_curr TO cisuser');
    g('GRANT SELECT ON cisadm.d1_msrmt_rpt_curr TO jrs2c2m');

    g('GRANT SELECT ON cisadm.ft_gl_distribution_rpt_curr TO cis_read');
    g('GRANT SELECT, INSERT, UPDATE, DELETE ON cisadm.ft_gl_distribution_rpt_curr TO cis_user');
    g('GRANT SELECT ON cisadm.ft_gl_distribution_rpt_curr TO cisread');
    g('GRANT SELECT ON cisadm.ft_gl_distribution_rpt_curr TO cisuser');
    g('GRANT SELECT ON cisadm.ft_gl_distribution_rpt_curr TO jrs2c2m');

    g('GRANT SELECT ON cisadm.d1_usage_rpt_curr TO cis_read');
    g('GRANT SELECT, INSERT, UPDATE, DELETE ON cisadm.d1_usage_rpt_curr TO cis_user');
    g('GRANT SELECT ON cisadm.d1_usage_rpt_curr TO cisread');
    g('GRANT SELECT ON cisadm.d1_usage_rpt_curr TO cisuser');
    g('GRANT SELECT ON cisadm.d1_usage_rpt_curr TO jrs2c2m');

    g('GRANT SELECT ON cisadm.d1_usage_scalar_dtl_rpt_curr TO cis_read');
    g('GRANT SELECT, INSERT, UPDATE, DELETE ON cisadm.d1_usage_scalar_dtl_rpt_curr TO cis_user');
    g('GRANT SELECT ON cisadm.d1_usage_scalar_dtl_rpt_curr TO cisread');
    g('GRANT SELECT ON cisadm.d1_usage_scalar_dtl_rpt_curr TO cisuser');
    g('GRANT SELECT ON cisadm.d1_usage_scalar_dtl_rpt_curr TO jrs2c2m');

    -- CMS SA + views
    g('GRANT SELECT ON cisadm.cms_sa_snapshot TO cis_read');
    g('GRANT SELECT, INSERT, UPDATE, DELETE ON cisadm.cms_sa_snapshot TO cis_user');
    g('GRANT SELECT ON cisadm.cms_sa_snapshot TO cisread');
    g('GRANT SELECT ON cisadm.cms_sa_snapshot TO cisuser');
    g('GRANT SELECT ON cisadm.cms_sa_snapshot TO jrs2c2m');

    g('GRANT SELECT ON cisadm.cms_d1_dvc_identifier_vw TO cis_read');
    g('GRANT SELECT ON cisadm.cms_d1_dvc_identifier_vw TO cis_user');
    g('GRANT SELECT ON cisadm.cms_d1_dvc_identifier_vw TO cisread');
    g('GRANT SELECT ON cisadm.cms_d1_dvc_identifier_vw TO cisuser');
    g('GRANT SELECT ON cisadm.cms_d1_dvc_identifier_vw TO jrs2c2m');

    g('GRANT SELECT ON cisadm.cms_d1_dvc_boda_vw TO cis_read');
    g('GRANT SELECT ON cisadm.cms_d1_dvc_boda_vw TO cis_user');
    g('GRANT SELECT ON cisadm.cms_d1_dvc_boda_vw TO cisread');
    g('GRANT SELECT ON cisadm.cms_d1_dvc_boda_vw TO cisuser');
    g('GRANT SELECT ON cisadm.cms_d1_dvc_boda_vw TO jrs2c2m');

    g('GRANT SELECT ON cisadm.cms_w1_asset_identifier_vw TO cis_read');
    g('GRANT SELECT ON cisadm.cms_w1_asset_identifier_vw TO cis_user');
    g('GRANT SELECT ON cisadm.cms_w1_asset_identifier_vw TO cisread');
    g('GRANT SELECT ON cisadm.cms_w1_asset_identifier_vw TO cisuser');
    g('GRANT SELECT ON cisadm.cms_w1_asset_identifier_vw TO jrs2c2m');

    g('GRANT SELECT ON cisadm.cms_c1_representative_boda_vw TO cis_read');
    g('GRANT SELECT ON cisadm.cms_c1_representative_boda_vw TO cis_user');
    g('GRANT SELECT ON cisadm.cms_c1_representative_boda_vw TO cisread');
    g('GRANT SELECT ON cisadm.cms_c1_representative_boda_vw TO cisuser');
    g('GRANT SELECT ON cisadm.cms_c1_representative_boda_vw TO jrs2c2m');

    g('GRANT SELECT ON cisadm.cms_d1_activity_char_vw TO cis_read');
    g('GRANT SELECT ON cisadm.cms_d1_activity_char_vw TO cis_user');
    g('GRANT SELECT ON cisadm.cms_d1_activity_char_vw TO cisread');
    g('GRANT SELECT ON cisadm.cms_d1_activity_char_vw TO cisuser');
    g('GRANT SELECT ON cisadm.cms_d1_activity_char_vw TO jrs2c2m');

    g('GRANT SELECT ON cisadm.cms_d1_activity_d1fa_boda_vw TO cis_read');
    g('GRANT SELECT ON cisadm.cms_d1_activity_d1fa_boda_vw TO cis_user');
    g('GRANT SELECT ON cisadm.cms_d1_activity_d1fa_boda_vw TO cisread');
    g('GRANT SELECT ON cisadm.cms_d1_activity_d1fa_boda_vw TO cisuser');
    g('GRANT SELECT ON cisadm.cms_d1_activity_d1fa_boda_vw TO jrs2c2m');

    g('GRANT SELECT ON cisadm.cms_ci_case_vw TO cis_read');
    g('GRANT SELECT ON cisadm.cms_ci_case_vw TO cis_user');
    g('GRANT SELECT ON cisadm.cms_ci_case_vw TO cisread');
    g('GRANT SELECT ON cisadm.cms_ci_case_vw TO cisuser');
    g('GRANT SELECT ON cisadm.cms_ci_case_vw TO jrs2c2m');

    g('GRANT SELECT ON cisadm.cms_ci_case_log_vw TO cis_read');
    g('GRANT SELECT ON cisadm.cms_ci_case_log_vw TO cis_user');
    g('GRANT SELECT ON cisadm.cms_ci_case_log_vw TO cisread');
    g('GRANT SELECT ON cisadm.cms_ci_case_log_vw TO cisuser');
    g('GRANT SELECT ON cisadm.cms_ci_case_log_vw TO jrs2c2m');
END;
/
