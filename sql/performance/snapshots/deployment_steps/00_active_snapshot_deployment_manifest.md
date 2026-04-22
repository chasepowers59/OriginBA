# Active Snapshot Deployment Manifest

This manifest is the source-of-truth map for the centralized deployment scripts in this folder.

| Snapshot | Table Script | Initial Baseline Procedure | Operational Procedure | Validation Script | Schedule Script | Rolling Window |
|---|---|---|---|---|---|---|
| `FT_RPT_CURR` | `finance/ft_rpt_curr/01_create_snapshot_table.sql` | `finance/ft_rpt_curr/02a_full_history_refresh_procedure.sql` | `finance/ft_rpt_curr/02_refresh_snapshot_procedure.sql` | `finance/ft_rpt_curr/11a_fast_before_after_validation.sql` | `finance/ft_rpt_curr/03_schedule_snapshot_job.sql` | `12 months` |
| `BSEG_BILLED_USAGE_RPT_CURR` | `billed_usage/bseg_billed_usage/01_create_snapshot_table.sql` | `billed_usage/bseg_billed_usage/02a_full_history_refresh_procedure.sql` | `billed_usage/bseg_billed_usage/02_refresh_snapshot_procedure.sql` | `billed_usage/bseg_billed_usage/04_validation_queries.sql` | `billed_usage/bseg_billed_usage/03_schedule_snapshot_job.sql` | `No` |
| `BSEG_SQ_USAGE_RPT_CURR` | `billed_usage/bseg_sq_usage/01_create_snapshot_table.sql` | `billed_usage/bseg_sq_usage/02a_full_history_refresh_procedure.sql` | `billed_usage/bseg_sq_usage/02_refresh_snapshot_procedure.sql` | `billed_usage/bseg_sq_usage/04_validation_queries.sql` | `billed_usage/bseg_sq_usage/03_schedule_snapshot_job.sql` | `No` |
| `D1_MSRMT_RPT_CURR` | `meter_ops/d1_msrmt/00_create_snapshot_table.sql` | `meter_ops/d1_msrmt/01a_full_history_refresh_procedure.sql` | `meter_ops/d1_msrmt/01_refresh_snapshot_procedure.sql` | `meter_ops/d1_msrmt/08_fast_before_after_validation.sql` | `meter_ops/d1_msrmt/02_schedule_snapshot_job.sql` | `12 months` |
| `FT_GL_DISTRIBUTION_RPT_CURR` | `finance/ft_gl_distribution/01_create_snapshot_table.sql` | `finance/ft_gl_distribution/02a_full_history_refresh_procedure.sql` | `finance/ft_gl_distribution/02_refresh_snapshot_procedure.sql` | `finance/ft_gl_distribution/11b_ultra_fast_before_after_validation.sql` | `finance/ft_gl_distribution/03_schedule_snapshot_job.sql` | `12 months` |
| `D1_USAGE_RPT_CURR` | `meter_ops/d1_usage/01_create_snapshot_table.sql` | `meter_ops/d1_usage/02a_full_history_refresh_procedure.sql` | `meter_ops/d1_usage/02_refresh_snapshot_procedure.sql` | `meter_ops/d1_usage/10_before_after_validation.sql` | `meter_ops/d1_usage/03_schedule_snapshot_job.sql` | `12 months` |
| `D1_USAGE_SCALAR_DTL_RPT_CURR` | `meter_ops/d1_usage_scalar_dtl/01_create_snapshot_table.sql` | `meter_ops/d1_usage_scalar_dtl/02a_full_history_refresh_procedure.sql` | `meter_ops/d1_usage_scalar_dtl/02_refresh_snapshot_procedure.sql` | `meter_ops/d1_usage_scalar_dtl/10_before_after_validation.sql` | `meter_ops/d1_usage_scalar_dtl/03_schedule_snapshot_job.sql` | `12 months` |

## Notes
- `BSEG_BILLED_USAGE_RPT_CURR` and `BSEG_SQ_USAGE_RPT_CURR` currently do not have approved rolling-window variants.
- Candidate BSEG rolling-window files now exist in the package folders, but they are not part of the active deployment flow until diagnostics and validation are completed.
- `FT_GL_DISTRIBUTION_RPT_CURR` uses the ultra-fast validator here because the heavier monthly parity validator is slow enough to block deployment flow.
- If a package-level file changes later, update this manifest and the wrapper script in this folder in the same change.
