PROMPT ============================================================
PROMPT Validate all domain support objects
PROMPT ============================================================

PROMPT [1/5] CMS_SA_SNAPSHOT
@@..\debt_mgmt\cms_sa_snapshot\04_validate_cms_sa_snapshot.sql

PROMPT [2/5] CMS_D1_DVC_IDENTIFIER_VW
@@..\meter_ops\cms_d1_dvc_identifier_view\02_validate_cms_d1_dvc_identifier_view.sql

PROMPT [3/5] CMS_D1_DVC_BODA_VW
@@..\meter_ops\cms_d1_dvc_boda_view\02_validate_cms_d1_dvc_boda_view.sql

PROMPT [4/5] CMS_W1_ASSET_IDENTIFIER_VW
@@..\meter_ops\cms_asset_identifier_view\02_validate_cms_w1_asset_identifier_view.sql

PROMPT [5/5] CMS Field Activity views
@@..\field_ops\cms_activity_views\02_validate_cms_activity_views.sql
