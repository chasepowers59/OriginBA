PROMPT Demo: remaining baseline refreshes (4-7)

PROMPT [4/7] D1_MSRMT_RPT_CURR
BEGIN
    cisadm.refresh_d1_msrmt_rpt_curr;
END;
/

PROMPT [5/7] FT_GL_DISTRIBUTION_RPT_CURR
BEGIN
    cisadm.refresh_ft_gl_distribution_rpt_curr;
END;
/

PROMPT [6/7] D1_USAGE_RPT_CURR
BEGIN
    cisadm.refresh_d1_usage_rpt_curr;
END;
/

PROMPT [7/7] D1_USAGE_SCALAR_DTL_RPT_CURR
BEGIN
    cisadm.refresh_d1_usage_scalar_dtl_rpt_curr;
END;
/
