# SmartCity Demo Snapshot Rollout Status

**Database:** Int Demo 2.9 (`smartcity-db-demo.originsmartops.com`)  
**Client alias:** `demo`  
**Rolling window:** 6 months (operational phase active)  
**Last updated:** 2026-05-21 (Phase B complete)

## Snapshot tables on demo (7/7 present with data)

| Snapshot table | Rows loaded | Status |
| --- | ---: | --- |
| `FT_RPT_CURR` | 62,986 | Populated |
| `BSEG_BILLED_USAGE_RPT_CURR` | 166,078 | Populated |
| `BSEG_SQ_USAGE_RPT_CURR` | 189,885 | Populated |
| `D1_MSRMT_RPT_CURR` | 10,409,822 | Populated |
| `FT_GL_DISTRIBUTION_RPT_CURR` | 108,865 | Populated |
| `D1_USAGE_RPT_CURR` | 27,462 | Populated |
| `D1_USAGE_SCALAR_DTL_RPT_CURR` | 28,844 | Populated |

All seven tables and `REFRESH_*` procedures are `VALID` in `CISADM`.

## Phase checklist

| Step | Status | Notes |
| --- | --- | --- |
| Preflight | Done | |
| Create 7 tables | Done | |
| Deploy full-history procedures | Done | |
| Baseline data load | Done | Manual immediate run after disabling staggered jobs |
| Baseline validation | Done | `04_validate_all_active_snapshots.sql` — all 7 passed 2026-05-21 |
| Deploy 6-month rolling procedures | Done | 2026-05-21 |
| Schedule 6-hour operational jobs | Done | 7 jobs enabled, 6-hour stagger |

## Operational schedules (6-hour cadence)

| Snapshot | Job | Enabled |
| --- | --- | --- |
| `FT_RPT_CURR` | `JOB_REFRESH_FT_RPT_CURR` | TRUE |
| `BSEG_BILLED_USAGE_RPT_CURR` | `JOB_REFRESH_BSEG_BILLED_USAGE_RPT_CURR` | TRUE |
| `BSEG_SQ_USAGE_RPT_CURR` | `REFRESH_BSEG_SQ_USAGE_RPT_CURR_JOB` | TRUE |
| `D1_MSRMT_RPT_CURR` | `JOB_REFRESH_D1_MSRMT_RPT_CURR` | TRUE |
| `FT_GL_DISTRIBUTION_RPT_CURR` | `JOB_REFRESH_FT_GL_DISTRIBUTION_RPT_CURR` | TRUE |
| `D1_USAGE_RPT_CURR` | `JOB_REFRESH_D1_USAGE_RPT_CURR` | TRUE |
| `D1_USAGE_SCALAR_DTL_RPT_CURR` | `JOB_REFRESH_D1_USAGE_SCALAR_DTL_RPT_CURR` | TRUE |

First scheduled runs began 2026-05-21 ~13:00 DB time. Each job uses a **6-month** rolling window; full baseline history outside that window is preserved.

## Jaspersoft import

Standard Offering demo import succeeded using rebuilt `standard_offering_Origin_DEMO_import.zip` (public template + Development snapshot Domains bundled). See [jaspersoft_environment_promotion_pipeline.md](jaspersoft_environment_promotion_pipeline.md).
