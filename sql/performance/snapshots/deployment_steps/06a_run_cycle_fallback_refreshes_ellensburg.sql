PROMPT Run refreshed cycle-fallback procedures on Ellensburg

PROMPT [1/3] BSEG_BILLED_USAGE_RPT_CURR
BEGIN
    cisadm.refresh_bseg_billed_usage_rpt_curr;
END;
/

PROMPT [2/3] BSEG_SQ_USAGE_RPT_CURR
BEGIN
    cisadm.refresh_bseg_sq_usage_rpt_curr;
END;
/

PROMPT [3/3] FT_GL_DISTRIBUTION_RPT_CURR
BEGIN
    cisadm.refresh_ft_gl_distribution_rpt_curr;
END;
/
