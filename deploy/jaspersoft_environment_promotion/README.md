# Jaspersoft Environment Promotion Staging

Use this folder for **non-client** promotions where repository org paths stay on
`Origin_DEV` and only the datasource alias/endpoints change (for example
`Origin_DEV_DS` -> `Origin_DEMO_DS`).

Tracked contents:

- `environment_profiles.json` — environment IDs, datasource JDBC settings, output ZIP stem
- `bundled/public_dashboard_template/` — shared dashboard JRXML required by Standard Offering dashboards (bundled into every demo import ZIP)

Do not commit:

- raw export ZIPs
- generated datasource export folders
- prepared import ZIPs

## Folder layout

- `incoming_exports/` — untouched DEV export ZIPs from Jaspersoft Server
- `incoming_datasources/` — generated or hand-maintained datasource exports per environment
- `prepared_imports/` — final import-ready ZIPs (for example `Origin_DEMO_import.zip`)
- `archive/` — original DEV export ZIPs after successful preparation

## Commands

Build or refresh the datasource export:

```bash
python3 scripts/jaspersoft/build_environment_datasource_export.py \
  --environment origin_demo \
  --out deploy/jaspersoft_environment_promotion/incoming_datasources/Origin_DEMO_DS \
  --force
```

Full environment pipeline (build datasource + rewrite package + archive):

```bash
python3 scripts/jaspersoft/run_environment_import_pipeline.py \
  --environment origin_demo \
  --source-zip deploy/jaspersoft_environment_promotion/incoming_exports/example.zip \
  --rebuild-datasource
```

Verify the prepared package:

```bash
python3 scripts/jaspersoft/verify_prepared_import.py \
  --zip deploy/jaspersoft_environment_promotion/prepared_imports/Origin_DEMO_import.zip \
  --target-org Origin_DEV \
  --target-ds Origin_DEMO_DS \
  --source-ds Origin_DEV_DS \
  --expect-datasource-overlay
```

## Standard packaging (every demo import)

The `origin_demo` pipeline always:

- rewrites `Origin_DEV_DS` → `Origin_DEMO_DS`
- bundles `/public/templates/actual_size.820.jrxml` from `bundled/public_dashboard_template/`
- merges `Workstreams/Development` snapshot Domains into `Standard_Offering/Development`
- regenerates tenant-root `.folder.xml` files and builds a tenant-safe `index.xml`

See [jaspersoft_environment_promotion_pipeline.md](/Users/chase/OriginBA-3/docs/jaspersoft_environment_promotion_pipeline.md).
