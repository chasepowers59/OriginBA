PROMPT ============================================================
PROMPT Deploy initial baseline refresh procedures
PROMPT ============================================================
PROMPT This script deploys the procedures used for the first full-history baseline load.

PROMPT [1/7] FT_RPT_CURR baseline procedure
@@..\finance\ft_rpt_curr\02a_full_history_refresh_procedure.sql

PROMPT [2/7] BSEG_BILLED_USAGE_RPT_CURR baseline procedure
@@..\billed_usage\bseg_billed_usage\02a_full_history_refresh_procedure.sql

PROMPT [3/7] BSEG_SQ_USAGE_RPT_CURR baseline procedure
@@..\billed_usage\bseg_sq_usage\02a_full_history_refresh_procedure.sql

PROMPT [4/7] D1_MSRMT_RPT_CURR baseline procedure
@@..\meter_ops\d1_msrmt\01a_full_history_refresh_procedure.sql

PROMPT [5/7] FT_GL_DISTRIBUTION_RPT_CURR baseline procedure
@@..\finance\ft_gl_distribution\02a_full_history_refresh_procedure.sql

PROMPT [6/7] D1_USAGE_RPT_CURR baseline procedure
@@..\meter_ops\d1_usage\02a_full_history_refresh_procedure.sql

PROMPT [7/7] D1_USAGE_SCALAR_DTL_RPT_CURR baseline procedure
@@..\meter_ops\d1_usage_scalar_dtl\02a_full_history_refresh_procedure.sql
