PROMPT ============================================================
PROMPT Run BSEG rolling-window candidate refreshes
PROMPT ============================================================

PROMPT [1/2] BSEG_BILLED_USAGE_RPT_CURR
BEGIN
    cisadm.refresh_bseg_billed_usage_rpt_curr;
END;
/

PROMPT [2/2] BSEG_SQ_USAGE_RPT_CURR
BEGIN
    cisadm.refresh_bseg_sq_usage_rpt_curr;
END;
/
