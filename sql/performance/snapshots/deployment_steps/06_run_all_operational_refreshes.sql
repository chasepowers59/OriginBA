PROMPT ============================================================
PROMPT Run operational refreshes
PROMPT ============================================================
PROMPT Execute this after deploying the operational procedures and before scheduling.

PROMPT [1/7] FT_RPT_CURR
BEGIN
    cisadm.refresh_ft_rpt_curr;
END;
/

PROMPT [2/7] BSEG_BILLED_USAGE_RPT_CURR
BEGIN
    cisadm.refresh_bseg_billed_usage_rpt_curr;
END;
/

PROMPT [3/7] BSEG_SQ_USAGE_RPT_CURR
BEGIN
    cisadm.refresh_bseg_sq_usage_rpt_curr;
END;
/

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
