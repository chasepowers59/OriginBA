PROMPT ============================================================
PROMPT Create scheduler jobs and apply active cadence
PROMPT ============================================================

PROMPT [1/8] FT_RPT_CURR scheduler job
@@..\finance\ft_rpt_curr\03_schedule_snapshot_job.sql

PROMPT [2/8] BSEG_BILLED_USAGE_RPT_CURR scheduler job
@@..\billed_usage\bseg_billed_usage\03_schedule_snapshot_job.sql

PROMPT [3/8] BSEG_SQ_USAGE_RPT_CURR scheduler job
@@..\billed_usage\bseg_sq_usage\03_schedule_snapshot_job.sql

PROMPT [4/8] D1_MSRMT_RPT_CURR scheduler job
@@..\meter_ops\d1_msrmt\02_schedule_snapshot_job.sql

PROMPT [5/8] FT_GL_DISTRIBUTION_RPT_CURR scheduler job
@@..\finance\ft_gl_distribution\03_schedule_snapshot_job.sql

PROMPT [6/8] D1_USAGE_RPT_CURR scheduler job
@@..\meter_ops\d1_usage\03_schedule_snapshot_job.sql

PROMPT [7/8] D1_USAGE_SCALAR_DTL_RPT_CURR scheduler job
@@..\meter_ops\d1_usage_scalar_dtl\03_schedule_snapshot_job.sql

PROMPT [8/8] CMS_SA_SNAPSHOT scheduler job
@@..\debt_mgmt\cms_sa_snapshot\05_schedule_cms_sa_snapshot_job.sql

PROMPT Apply the approved 6-hour staggered cadence to all active jobs
@@..\apply_6hour_staggered_schedule_1am_base.sql
