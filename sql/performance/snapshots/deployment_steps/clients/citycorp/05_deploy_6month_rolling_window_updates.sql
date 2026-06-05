PROMPT ============================================================
PROMPT CityCorp: deploy 6-month rolling-window operational procedures
PROMPT ============================================================
PROMPT All active snapshots use a 6-month maintenance window on CityCorp.

PROMPT [1/7] FT_RPT_CURR operational procedure (6-month window)
@@..\..\..\finance\ft_rpt_curr\02_refresh_snapshot_procedure_6month.sql

PROMPT [2/7] BSEG_BILLED_USAGE_RPT_CURR operational procedure (6-month window)
@@..\..\..\billed_usage\bseg_billed_usage\02_refresh_snapshot_procedure_6month.sql

PROMPT [3/7] BSEG_SQ_USAGE_RPT_CURR operational procedure (6-month window)
@@..\..\..\billed_usage\bseg_sq_usage\02_refresh_snapshot_procedure_6month.sql

PROMPT [4/7] D1_MSRMT_RPT_CURR operational procedure (6-month window)
@@..\..\..\meter_ops\d1_msrmt\01_refresh_snapshot_procedure_6month.sql

PROMPT [5/7] FT_GL_DISTRIBUTION_RPT_CURR operational procedure (6-month window)
@@..\..\..\finance\ft_gl_distribution\02_refresh_snapshot_procedure.sql

PROMPT [6/7] D1_USAGE_RPT_CURR operational procedure (6-month window)
@@..\..\..\meter_ops\d1_usage\02_refresh_snapshot_procedure_6month.sql

PROMPT [7/7] D1_USAGE_SCALAR_DTL_RPT_CURR operational procedure (6-month window)
@@..\..\..\meter_ops\d1_usage_scalar_dtl\02_refresh_snapshot_procedure_6month.sql
