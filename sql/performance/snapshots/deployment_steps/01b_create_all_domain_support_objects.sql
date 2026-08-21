PROMPT ============================================================
PROMPT Create domain support objects (CMS views + CMS_SA_SNAPSHOT)
PROMPT ============================================================

PROMPT [1/7] CMS_SA_SNAPSHOT table
@@..\debt_mgmt\cms_sa_snapshot\01_create_cms_sa_snapshot_table.sql

PROMPT [2/7] CM_SNAPSHOT_TYPE_FLG lookups (required by Domain Ad Hoc inner joins)
@@..\debt_mgmt\cms_sa_snapshot\06_seed_cm_snapshot_type_flg_lookups.sql

PROMPT [3/7] CMS_D1_DVC_IDENTIFIER_VW
@@..\meter_ops\cms_d1_dvc_identifier_view\01_create_cms_d1_dvc_identifier_view.sql

PROMPT [4/7] CMS_D1_DVC_BODA_VW
@@..\meter_ops\cms_d1_dvc_boda_view\01_create_cms_d1_dvc_boda_view.sql

PROMPT [5/7] CMS_W1_ASSET_IDENTIFIER_VW
@@..\meter_ops\cms_asset_identifier_view\01_create_cms_w1_asset_identifier_view.sql

PROMPT [6/7] CMS Field Activity views
@@..\field_ops\cms_activity_views\01_create_cms_activity_views.sql

PROMPT [7/7] CMS Case views (Standard Offering Case Domain)
@@..\customer_ops\cms_ci_case_views\01_create_cms_ci_case_views.sql
