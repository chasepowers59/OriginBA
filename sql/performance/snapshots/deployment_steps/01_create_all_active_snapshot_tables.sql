PROMPT ============================================================
PROMPT Create all active snapshot tables
PROMPT ============================================================

PROMPT [1/7] FT_RPT_CURR
@@..\finance\ft_rpt_curr\01_create_snapshot_table.sql

PROMPT [2/7] BSEG_BILLED_USAGE_RPT_CURR
@@..\billed_usage\bseg_billed_usage\01_create_snapshot_table.sql

PROMPT [3/7] BSEG_SQ_USAGE_RPT_CURR
@@..\billed_usage\bseg_sq_usage\01_create_snapshot_table.sql

PROMPT [4/7] D1_MSRMT_RPT_CURR
@@..\meter_ops\d1_msrmt\00_create_snapshot_table.sql

PROMPT [5/7] FT_GL_DISTRIBUTION_RPT_CURR
@@..\finance\ft_gl_distribution\01_create_snapshot_table.sql

PROMPT [6/7] D1_USAGE_RPT_CURR
@@..\meter_ops\d1_usage\01_create_snapshot_table.sql

PROMPT [7/7] D1_USAGE_SCALAR_DTL_RPT_CURR
@@..\meter_ops\d1_usage_scalar_dtl\01_create_snapshot_table.sql
