PROMPT ============================================================
PROMPT Validate all active snapshots
PROMPT ============================================================
PROMPT Reuse this script after baseline load and after operational cutover.

PROMPT [1/7] FT_RPT_CURR validation
@@..\finance\ft_rpt_curr\11a_fast_before_after_validation.sql

PROMPT [2/7] BSEG_BILLED_USAGE_RPT_CURR validation
@@..\billed_usage\bseg_billed_usage\04_validation_queries.sql

PROMPT [3/7] BSEG_SQ_USAGE_RPT_CURR validation
@@..\billed_usage\bseg_sq_usage\04_validation_queries.sql

PROMPT [4/7] D1_MSRMT_RPT_CURR validation
@@..\meter_ops\d1_msrmt\08_fast_before_after_validation.sql

PROMPT [5/7] FT_GL_DISTRIBUTION_RPT_CURR validation
@@..\finance\ft_gl_distribution\11b_ultra_fast_before_after_validation.sql

PROMPT [6/7] D1_USAGE_RPT_CURR validation
@@..\meter_ops\d1_usage\10_before_after_validation.sql

PROMPT [7/7] D1_USAGE_SCALAR_DTL_RPT_CURR validation
@@..\meter_ops\d1_usage_scalar_dtl\10_before_after_validation.sql
