PROMPT ============================================================
PROMPT Rerun Odessa DEV refreshes after cycle fallback hardening
PROMPT ============================================================

PROMPT [1/5] BSEG_BILLED_USAGE_RPT_CURR
BEGIN
    cisadm.refresh_bseg_billed_usage_rpt_curr;
END;
/

PROMPT [2/5] BSEG_SQ_USAGE_RPT_CURR
BEGIN
    cisadm.refresh_bseg_sq_usage_rpt_curr;
END;
/

PROMPT [3/5] FT_GL_DISTRIBUTION_RPT_CURR
BEGIN
    cisadm.refresh_ft_gl_distribution_rpt_curr;
END;
/

PROMPT [4/5] D1_USAGE_RPT_CURR
BEGIN
    cisadm.refresh_d1_usage_rpt_curr;
END;
/

PROMPT [5/5] D1_USAGE_SCALAR_DTL_RPT_CURR
BEGIN
    cisadm.refresh_d1_usage_scalar_dtl_rpt_curr;
END;
/
