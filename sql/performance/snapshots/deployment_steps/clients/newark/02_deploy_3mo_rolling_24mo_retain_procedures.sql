-- Deploy active-7 refresh procedures to Newark TEST
-- Windows: historical seed = 24 months; operational rolling = 3 months + 24-month retention purge

@@../../../billed_usage/bseg_billed_usage/02_refresh_snapshot_procedure.sql
@@../../../billed_usage/bseg_sq_usage/02_refresh_snapshot_procedure.sql
@@../../../finance/ft_rpt_curr/02_refresh_snapshot_procedure.sql
@@../../../finance/ft_gl_distribution/02_refresh_snapshot_procedure.sql
@@../../../meter_ops/d1_msrmt/01_refresh_snapshot_procedure.sql
@@../../../meter_ops/d1_usage/02_refresh_snapshot_procedure.sql
@@../../../meter_ops/d1_usage_scalar_dtl/02_refresh_snapshot_procedure.sql

PROMPT Deployed Newark operational procedures (3-month refresh / 24-month retain)
