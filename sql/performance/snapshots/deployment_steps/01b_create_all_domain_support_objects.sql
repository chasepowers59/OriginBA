PROMPT ============================================================
PROMPT Create domain support objects (CMS views + CMS_SA_SNAPSHOT)
PROMPT ============================================================

PROMPT [1/5] CMS_SA_SNAPSHOT table
@@..\debt_mgmt\cms_sa_snapshot\01_create_cms_sa_snapshot_table.sql

PROMPT [2/5] CMS_D1_DVC_IDENTIFIER_VW
@@..\meter_ops\cms_d1_dvc_identifier_view\01_create_cms_d1_dvc_identifier_view.sql

PROMPT [3/5] CMS_D1_DVC_BODA_VW
@@..\meter_ops\cms_d1_dvc_boda_view\01_create_cms_d1_dvc_boda_view.sql

PROMPT [4/5] CMS_W1_ASSET_IDENTIFIER_VW
@@..\meter_ops\cms_asset_identifier_view\01_create_cms_w1_asset_identifier_view.sql

PROMPT [5/5] CMS Field Activity views
@@..\field_ops\cms_activity_views\01_create_cms_activity_views.sql
