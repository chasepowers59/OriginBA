# Jaspersoft (OriginBA-3 side): delivery

This repo owns everything about getting reports and domains INTO a Jaspersoft server. The
domains built over the dbt reporting canvases are generated in the data repo:
`~/originba_dbt/jaspersoft/README.md`. Paths below stay where scripts and CI pin them; this
page is the index.

| Topic | Canonical home | Skill |
| --- | --- | --- |
| Generated domains (dbt canvases, `<CANVAS>_BI` views) | `~/originba_dbt/jaspersoft/domains/<target>/` | `jaspersoft-domain-generation` (dbt repo) |
| Hand-built domains (CISADM joins, active-8 snapshots) | `domains/exports/manual_imports/` (7 active-8 XML, report packages); `domains/manual_imports/newark_*` (client deliverables); `domains/working/` (temporary) | `.claude/skills/originba-jaspersoft-domain-modeling` |
| JRXML reports + input controls | `reports/`, `server/input_controls/` (paired `<report>_input_controls{,_rest}.json`), `deploy/build_report_unit*.sh` | `.claude/skills/originba-jrxml-report-builder`; style: `origin-doc-style` (dbt repo) |
| Client promotion and tenant imports | `deploy/jaspersoft_client_promotion/`, `scripts/jaspersoft/{prepare_client_imports,build_client_tenant_report_import,verify_prepared_import,run_client_import_pipeline}.py` | `.claude/skills/jaspersoft-client-tenant-import`, `originba-client-promotion` |
| Environment promotion (Origin_DEV -> STAGE etc.) | `deploy/jaspersoft_environment_promotion/`, `scripts/jaspersoft/promotion_environments.py` | -- |
| DataSources per client and per internal environment | `deploy/jaspersoft_datasources/{canonical,clients}/` -- names declared in `~/originba_dbt/clients.yml` | -- |
| The shipped Standard Offering package (binds only the active-8) | `deploy/jaspersoft_standard_offering/` | -- |
| Dashboards | `jaspersoft/dashboards/{native,snapshot}_dashboard_pack_v1/`, `scripts/jaspersoft/package_native_dashboard.py` | -- |
| Snapshot operations (the active-8) | `sql/performance/snapshots/` and its `docs/` | `originba-snapshot-rollout-qa` |
| Delivery standards, runbooks, export anatomy, troubleshooting | `jaspersoft/docs/` (moved from `docs/` 2026-09-08; `docs/MOVED.md` lists them) | -- |
| Per-report and QA signoff | `jaspersoft/docs/ar_aging_asof_report_import.md`, `scripts/doc/build_standard_offering_validation_doc.py` | `originba-validation-signoff` |

**Resolutions written here so they stop being re-derived (2026-09-08)**

- Resource roots: authoring exports use `/organizations/organization_1/organizations/Origin_DEV/SmartCity/...`;
  client tenant imports are tenant-relative `/SmartCity/...` with no `rootTenantId`; the `Standard_Offering` folder
  sits under either. Three pipeline stages, not three conventions.
- Item ids: `output/domain_field_index.json` for hand-built domains; `~/originba_dbt/scripts/bi_names.py` for generated ones.
- Style: Origin 2025 (Aptos, Sapphire `#006FAC`); Blue Theme only to match an existing Standard Offering family.
- Counts: the shipped package's own README is the count of record; "104 reports" and "235 reports / 52 domains" were pre-package inventories.
- The active snapshot set is eight tables; the dashboards' "native" pack binds live CISADM, the "snapshot" pack binds the active-8.
- Odessa's DataSource name is recorded twice (`Origin_DataVergence_DS`, `Odessa_DS`) until a read of the live tenant settles it (registry Phase 4 gate).
