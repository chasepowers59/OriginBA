# CMS_D1_DVC_IDENTIFIER_VW (legacy device identifier overlay)

## Why this exists

Standard Offering **Device - Domain** expects physical view:

- `CISADM.CMS_D1_DVC_IDENTIFIER_VW`

This object provides one-row-per-device identifier overlay fields (asset id, badge, configuration, serial, external IDs, NIC/utility fields) from `D1_DVC_IDENTIFIER`.

CityCorp had an invalid `CISADM290` copy while `CISREAD` synonym targeted missing `CISADM.CMS_D1_DVC_IDENTIFIER_VW`, which can trigger Domain Designer warning/deletes for device-domain join trees.

## Scripts

1. `01_create_cms_d1_dvc_identifier_view.sql` — create view, grants, CISREAD synonym
2. `02_validate_cms_d1_dvc_identifier_view.sql` — object/synonym status, row counts, join smoke

## CityCorp deploy

```bash
python3 scripts/local/run_client_oracle_sql.py --client citycorp   --file sql/performance/snapshots/meter_ops/cms_d1_dvc_identifier_view/01_create_cms_d1_dvc_identifier_view.sql

python3 scripts/local/run_client_oracle_sql.py --client citycorp   --file sql/performance/snapshots/meter_ops/cms_d1_dvc_identifier_view/02_validate_cms_d1_dvc_identifier_view.sql
```

## Notes

- This is a **view**, not a refresh table.
- Source truth is live `CISADM.D1_DVC_IDENTIFIER`.
- `DEVICE_SP_RPT_CURR` already uses this object as the governed device identifier overlay.
