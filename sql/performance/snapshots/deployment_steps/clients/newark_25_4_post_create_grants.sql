PROMPT ============================================================
PROMPT Apply object grants via CISADM.originba_ddl_helper
PROMPT ============================================================

BEGIN
    -- Active 7 snapshot tables
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.ft_rpt_curr TO cis_read');
    cisadm.originba_ddl_helper2('GRANT SELECT, INSERT, UPDATE, DELETE ON cisadm.ft_rpt_curr TO cis_user');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.ft_rpt_curr TO cisread');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.ft_rpt_curr TO cisuser');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.ft_rpt_curr TO jrs2c2m');

    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.bseg_billed_usage_rpt_curr TO cis_read');
    cisadm.originba_ddl_helper2('GRANT SELECT, INSERT, UPDATE, DELETE ON cisadm.bseg_billed_usage_rpt_curr TO cis_user');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.bseg_billed_usage_rpt_curr TO cisread');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.bseg_billed_usage_rpt_curr TO cisuser');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.bseg_billed_usage_rpt_curr TO jrs2c2m');

    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.bseg_sq_usage_rpt_curr TO cis_read');
    cisadm.originba_ddl_helper2('GRANT SELECT, INSERT, UPDATE, DELETE ON cisadm.bseg_sq_usage_rpt_curr TO cis_user');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.bseg_sq_usage_rpt_curr TO cisread');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.bseg_sq_usage_rpt_curr TO cisuser');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.bseg_sq_usage_rpt_curr TO jrs2c2m');

    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.d1_msrmt_rpt_curr TO cis_read');
    cisadm.originba_ddl_helper2('GRANT SELECT, INSERT, UPDATE, DELETE ON cisadm.d1_msrmt_rpt_curr TO cis_user');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.d1_msrmt_rpt_curr TO cisread');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.d1_msrmt_rpt_curr TO cisuser');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.d1_msrmt_rpt_curr TO jrs2c2m');

    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.ft_gl_distribution_rpt_curr TO cis_read');
    cisadm.originba_ddl_helper2('GRANT SELECT, INSERT, UPDATE, DELETE ON cisadm.ft_gl_distribution_rpt_curr TO cis_user');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.ft_gl_distribution_rpt_curr TO cisread');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.ft_gl_distribution_rpt_curr TO cisuser');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.ft_gl_distribution_rpt_curr TO jrs2c2m');

    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.d1_usage_rpt_curr TO cis_read');
    cisadm.originba_ddl_helper2('GRANT SELECT, INSERT, UPDATE, DELETE ON cisadm.d1_usage_rpt_curr TO cis_user');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.d1_usage_rpt_curr TO cisread');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.d1_usage_rpt_curr TO cisuser');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.d1_usage_rpt_curr TO jrs2c2m');

    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.d1_usage_scalar_dtl_rpt_curr TO cis_read');
    cisadm.originba_ddl_helper2('GRANT SELECT, INSERT, UPDATE, DELETE ON cisadm.d1_usage_scalar_dtl_rpt_curr TO cis_user');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.d1_usage_scalar_dtl_rpt_curr TO cisread');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.d1_usage_scalar_dtl_rpt_curr TO cisuser');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.d1_usage_scalar_dtl_rpt_curr TO jrs2c2m');

    -- CMS SA + views
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.cms_sa_snapshot TO cis_read');
    cisadm.originba_ddl_helper2('GRANT SELECT, INSERT, UPDATE, DELETE ON cisadm.cms_sa_snapshot TO cis_user');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.cms_sa_snapshot TO cisread');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.cms_sa_snapshot TO cisuser');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.cms_sa_snapshot TO jrs2c2m');

    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.cms_d1_dvc_identifier_vw TO cis_read');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.cms_d1_dvc_identifier_vw TO cis_user');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.cms_d1_dvc_identifier_vw TO cisread');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.cms_d1_dvc_identifier_vw TO cisuser');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.cms_d1_dvc_identifier_vw TO jrs2c2m');

    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.cms_d1_dvc_boda_vw TO cis_read');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.cms_d1_dvc_boda_vw TO cis_user');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.cms_d1_dvc_boda_vw TO cisread');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.cms_d1_dvc_boda_vw TO cisuser');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.cms_d1_dvc_boda_vw TO jrs2c2m');

    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.cms_w1_asset_identifier_vw TO cis_read');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.cms_w1_asset_identifier_vw TO cis_user');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.cms_w1_asset_identifier_vw TO cisread');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.cms_w1_asset_identifier_vw TO cisuser');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.cms_w1_asset_identifier_vw TO jrs2c2m');

    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.cms_c1_representative_boda_vw TO cis_read');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.cms_c1_representative_boda_vw TO cis_user');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.cms_c1_representative_boda_vw TO cisread');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.cms_c1_representative_boda_vw TO cisuser');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.cms_c1_representative_boda_vw TO jrs2c2m');

    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.cms_d1_activity_char_vw TO cis_read');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.cms_d1_activity_char_vw TO cis_user');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.cms_d1_activity_char_vw TO cisread');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.cms_d1_activity_char_vw TO cisuser');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.cms_d1_activity_char_vw TO jrs2c2m');

    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.cms_d1_activity_d1fa_boda_vw TO cis_read');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.cms_d1_activity_d1fa_boda_vw TO cis_user');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.cms_d1_activity_d1fa_boda_vw TO cisread');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.cms_d1_activity_d1fa_boda_vw TO cisuser');
    cisadm.originba_ddl_helper2('GRANT SELECT ON cisadm.cms_d1_activity_d1fa_boda_vw TO jrs2c2m');
END;
/
