# Domain Support Deployment Manifest

These objects keep Standard Offering Jaspersoft Domains working alongside the active 7 governed snapshot tables. They are deployed and validated in the same client rollout workflow but are **not** rolling-window `_RPT_CURR` snapshots.

## Debt Management — refreshable table

| Object | Type | Create Script | Procedure Script | Refresh | Validation | Install Gate |
|---|---|---|---|---|---|---|
| `CMS_SA_SNAPSHOT` | Table + procedure | `debt_mgmt/cms_sa_snapshot/01_create_cms_sa_snapshot_table.sql` | `debt_mgmt/cms_sa_snapshot/02_refresh_cms_sa_snapshot_procedure.sql` | `03e_run_domain_support_refreshes.sql` | `debt_mgmt/cms_sa_snapshot/04_validate_cms_sa_snapshot.sql` | `04d_domain_support_install_validation_gate.sql` |
| `CM_SNAPSHOT_TYPE_FLG` | Lookup seed (`CI_LOOKUP_VAL` / `_L`) | `debt_mgmt/cms_sa_snapshot/06_seed_cm_snapshot_type_flg_lookups.sql` | — | included in `01b` | Ad Hoc returns rows when joining lookup | — |

Notes:

- `CMS_ACCT_SNAPSHOT` is a **Domain derived query** over `CMS_SA_SNAPSHOT`; no separate deploy object.
- Domains inner-join `CI_LOOKUP_VAL_L` on `CM_SNAPSHOT_TYPE_FLG` (values `LDAY`/`EMON`/`ARCH`/`LEMN`). Fresh DBs without this seed return zero Ad Hoc rows.
- Refresh uses payments/credits, excludes future `ARS_DT`, and applies FIFO aging (`ARS_AMT1`–`ARS_AMT5` sum to `CUR_BAL`).
- Longer-term replacement: `SA_AGED_BAL_RPT_CURR`.

## Meter Operations — live views

| Object | Create Script | Validation Script |
|---|---|---|
| `CMS_D1_DVC_IDENTIFIER_VW` | `meter_ops/cms_d1_dvc_identifier_view/01_create_cms_d1_dvc_identifier_view.sql` | `meter_ops/cms_d1_dvc_identifier_view/02_validate_cms_d1_dvc_identifier_view.sql` |
| `CMS_D1_DVC_BODA_VW` | `meter_ops/cms_d1_dvc_boda_view/01_create_cms_d1_dvc_boda_view.sql` | `meter_ops/cms_d1_dvc_boda_view/02_validate_cms_d1_dvc_boda_view.sql` |
| `CMS_W1_ASSET_IDENTIFIER_VW` | `meter_ops/cms_asset_identifier_view/01_create_cms_w1_asset_identifier_view.sql` | `meter_ops/cms_asset_identifier_view/02_validate_cms_w1_asset_identifier_view.sql` |

## Field Operations — live views

| Object | Create Script | Validation Script |
|---|---|---|
| `CMS_C1_REPRESENTATIVE_BODA_VW` | `field_ops/cms_activity_views/01_create_cms_activity_views.sql` | `field_ops/cms_activity_views/02_validate_cms_activity_views.sql` |
| `CMS_D1_ACTIVITY_CHAR_VW` | `field_ops/cms_activity_views/01_create_cms_activity_views.sql` | `field_ops/cms_activity_views/02_validate_cms_activity_views.sql` |
| `CMS_D1_ACTIVITY_D1FA_BODA_VW` | `field_ops/cms_activity_views/01_create_cms_activity_views.sql` | `field_ops/cms_activity_views/02_validate_cms_activity_views.sql` |

## Customer Operations — live views

| Object | Create Script | Notes |
|---|---|---|
| `CMS_CI_CASE_VW` | `customer_ops/cms_ci_case_views/01_create_cms_ci_case_views.sql` | Required by Standard Offering Case Domain (create/close timing + duration) |
| `CMS_CI_CASE_LOG_VW` | `customer_ops/cms_ci_case_views/01_create_cms_ci_case_views.sql` | Case log timeline / state durations |

## Centralized wrapper scripts (this folder)

| Step | Script | Purpose |
|---|---|---|
| Create | `01b_create_all_domain_support_objects.sql` | Tables + CMS views + grants/synonyms |
| Deploy procedure | `02b_deploy_domain_support_procedures.sql` | `REFRESH_CMS_SA_SNAPSHOT` |
| Refresh | `03e_run_domain_support_refreshes.sql` | Run CMS SA refresh (manual / cutover) |
| Validate | `04c_validate_all_domain_support_objects.sql` | Full validation pack |
| Install gate | `04d_domain_support_install_validation_gate.sql` | Fail-fast QA (`--fail-if-any-rows`) |

## Rollout placement (with active 7)

1. `01_create_all_active_snapshot_tables.sql`
2. **`01b_create_all_domain_support_objects.sql`**
3. `02_deploy_all_initial_full_history_procedures.sql`
4. **`02b_deploy_domain_support_procedures.sql`**
5. Baseline jobs / refreshes for the active 7
6. **`03e_run_domain_support_refreshes.sql`** (can run in parallel with baseline; uses live `CI_FT`)
7. `04_validate_all_active_snapshots.sql`
8. **`04c_validate_all_domain_support_objects.sql`**
9. `04b_snapshot_install_validation_gate.sql`
10. **`04d_domain_support_install_validation_gate.sql`**

Operational cutover (`06_run_all_operational_refreshes.sql`) includes CMS SA refresh as step 8.
