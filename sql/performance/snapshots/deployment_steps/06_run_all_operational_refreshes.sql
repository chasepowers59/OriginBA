PROMPT ============================================================
PROMPT Run operational refreshes
PROMPT ============================================================
PROMPT Execute this after deploying the operational procedures and before scheduling.

PROMPT [1/8] FT_RPT_CURR
BEGIN
    cisadm.refresh_ft_rpt_curr;
END;
/

PROMPT [2/8] BSEG_BILLED_USAGE_RPT_CURR
BEGIN
    cisadm.refresh_bseg_billed_usage_rpt_curr;
END;
/

PROMPT [3/8] BSEG_SQ_USAGE_RPT_CURR
BEGIN
    cisadm.refresh_bseg_sq_usage_rpt_curr;
END;
/

PROMPT [4/8] D1_MSRMT_RPT_CURR
BEGIN
    cisadm.refresh_d1_msrmt_rpt_curr;
END;
/

PROMPT [5/8] FT_GL_DISTRIBUTION_RPT_CURR
BEGIN
    cisadm.refresh_ft_gl_distribution_rpt_curr;
END;
/

PROMPT [6/8] D1_USAGE_RPT_CURR
BEGIN
    cisadm.refresh_d1_usage_rpt_curr;
END;
/

PROMPT [7/8] D1_USAGE_SCALAR_DTL_RPT_CURR
BEGIN
    cisadm.refresh_d1_usage_scalar_dtl_rpt_curr;
END;
/

PROMPT [8/8] CMS_SA_SNAPSHOT (domain support)
BEGIN
    cisadm.refresh_cms_sa_snapshot;
END;
/
