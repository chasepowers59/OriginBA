# Canonical Jaspersoft Data Sources (Internal)

Source-of-truth JDBC datasource exports for **internal** SmartCity environments.
Client databases use separate per-client datasource aliases (`Ellensburg_DS`, etc.)
under `clients/`.

## Canonical exports

| Alias | Tenant | Purpose | Folder |
| --- | --- | --- | --- |
| `Origin_STAGE_DS` | `Origin_STAGE` | pstgdb (primary Stage DB) | `canonical/Origin_STAGE_DS/` |
| `Training_DB` | `Origin_STAGE` | ptrndb Int Train (snapshots) | `canonical/Training_DB/` |
| `Origin_DEV_DS` | `Origin_DEV` | Org primary DEV alias (repo copy = INT_DEV; server may differ) | `canonical/Origin_DEV_DS/` |
| `Origin_INT_DEV_DS` | `Origin_DEV` | INT_DEV / pdevdb 25.4 (dbt warehouse) — safe beside Ellensburg `Origin_DEV_DS` | `canonical/Origin_INT_DEV_DS/` |

**Origin_STAGE_DS pstgdb backup:** `archive/Origin_STAGE_DS_pstgdb_20260608/`

Stage Standard Offering imports use `Training_DB` only; they do not overwrite `Origin_STAGE_DS`.

Each folder contains the exact Jaspersoft export:

- `resources/DataSource/<alias>.xml`
- `resources/DataSource/.folder.xml`
- `index.xml`

Original ZIP backups: `Origin_STAGE_DS_export.zip`, `Origin_DEV_DS_export.zip`, `Origin_INT_DEV_DS_export.zip`.

If server `Origin_DEV_DS` already points at a client TEST DB (e.g. Ellensburg), import **`Origin_INT_DEV_DS`** for pdevdb warehouse work so you do not overwrite that alias.

## Refresh from Jaspersoft Server

When a datasource changes on the server, re-export `/DataSource/<alias>` from inside
the tenant and run:

```bash
python3 scripts/jaspersoft/store_canonical_datasource_export.py \
  --alias Origin_STAGE_DS \
  --zip "/path/to/export.zip"
```

## Standard Offering packages

Build **two** import ZIPs (one per internal datasource):

```bash
python3 scripts/jaspersoft/run_internal_standard_offering_pipeline.py \
  --source-zip "/path/to/standard offering.zip"
```

Outputs:

- `deploy/jaspersoft_environment_promotion/prepared_imports/standard_offering_Origin_STAGE_import.zip`
- `deploy/jaspersoft_environment_promotion/prepared_imports/standard_offering_Origin_DEV_import.zip`

Each package rewrites all `Origin_DEV_DS` references to the target alias and injects
the canonical datasource XML — the old datasource is removed from the bundle.
