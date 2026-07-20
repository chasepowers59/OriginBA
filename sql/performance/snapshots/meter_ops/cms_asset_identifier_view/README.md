# CMS_W1_ASSET_IDENTIFIER_VW (legacy asset identifier overlay)

## Why this exists

Standard Offering **Asset - Domain** expects physical view:

- `CISADM.CMS_W1_ASSET_IDENTIFIER_VW`

This object provides one-row-per-asset identifier overlay fields (external id, pallet, serial, badge, purchase order, firmware values) from `W1_ASSET_IDENTIFIER`.

CityCorp had a `CISREAD` synonym targeting `CISADM.CMS_W1_ASSET_IDENTIFIER_VW` while the CISADM view was missing, which can trigger Domain Designer warning/deletes for the Asset Identifier table in `JoinTree_1`.

## Scripts

1. `01_create_cms_w1_asset_identifier_view.sql` — create view, grants, CISREAD synonym
2. `02_validate_cms_w1_asset_identifier_view.sql` — object/synonym status, row counts, join smoke

## CityCorp deploy

```bash
python3 scripts/local/run_client_oracle_sql.py --client citycorp   --file sql/performance/snapshots/meter_ops/cms_asset_identifier_view/01_create_cms_w1_asset_identifier_view.sql

python3 scripts/local/run_client_oracle_sql.py --client citycorp   --file sql/performance/snapshots/meter_ops/cms_asset_identifier_view/02_validate_cms_w1_asset_identifier_view.sql
```

## Notes

- This is a **view**, not a refresh table.
- Source truth is live `CISADM.W1_ASSET_IDENTIFIER`.
- `DEVICE_SP_RPT_CURR` already uses this object as the governed asset identifier overlay.
