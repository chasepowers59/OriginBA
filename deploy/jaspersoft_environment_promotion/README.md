# Jaspersoft Environment Promotion Staging

Use this folder for **non-client** promotions where repository org paths stay on
`Origin_DEV` and only the datasource alias/endpoints change (for example
`Origin_DEV_DS` -> `Training_DB` on Stage).

## Import rule (all promotions)

Build packages with **light-touch tenant-root** settings and import **inside the
target tenant** (Repository → Import). Do not import these ZIPs from server root.

See [jaspersoft_environment_promotion_pipeline.md](/Users/chase/OriginBA-3/docs/jaspersoft_environment_promotion_pipeline.md)
— **Standard promotion contract**.

Tracked contents:

- `environment_profiles.json` — environment IDs, datasource JDBC settings, output ZIP stem
- `bundled/public_dashboard_template/` — shared dashboard JRXML required by Standard Offering dashboards (bundled into every demo import ZIP)

Internal canonical datasource exports (committed):

- [Origin_STAGE_DS](../jaspersoft_datasources/canonical/Origin_STAGE_DS) — pstgdb (unchanged by SO import)
- [Training_DB](../jaspersoft_datasources/canonical/Training_DB) — ptrndb snapshots (Stage SO import)
- [Origin_DEV_DS](../jaspersoft_datasources/canonical/Origin_DEV_DS)

Build both internal Standard Offering import ZIPs from the tenant-root export:

```bash
python3 scripts/jaspersoft/run_internal_standard_offering_pipeline.py \
  --source-zip "/path/to/standard offering.zip"
```

The pipeline auto-detects tenant-root `Standard_Offering` exports and skips the legacy
102-report Workstreams curation build. Validation checks `147` Ad Hoc views, `13`
dashboards, datasource overlay, and public dashboard template bundling.

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
