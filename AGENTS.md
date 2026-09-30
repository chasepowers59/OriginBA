# OriginBA Assistant Contract

## Objective
Build and maintain Oracle C2M + Jaspersoft Studio/Server reports using **Domain-first** design, production-safe conventions, and deployment compliance.

## Non-Negotiables
1. Prefer **Domain-based JRXML** (`language="domain"`) unless explicitly requested to use raw SQL.
2. Never embed credentials in JRXML/SQL/scripts.
3. Use datasource aliases only, as declared per client in `~/originba_dbt/clients.yml` (`jaspersoft.ds_name`) and exported under `deploy/jaspersoft_datasources/`.
4. Keep JRXML compatible with Jaspersoft Studio/Server 9.x schema ordering.
5. For any report change, also maintain matching input controls under `server/input_controls/`.
6. Preserve organization isolation (`Origin_DEV` source context by default).
7. Choose the artifact intentionally: Domain for shared governed semantic layers, Report for pixel-perfect delivery, Ad Hoc for self-service analysis, Dashboard for multi-panel consumption, Topic for curated self-service entry.
8. Use raw Domain tables only when joins preserve the intended grain without fan-out; if row preservation is at risk, establish the grain in Oracle first with governed SQL or a derived table.

## Source of Truth (2026-09-08)
1. Canvases and their fields: `output/catalog_dbt.json` (38 canvases; generated in `~/originba_dbt`).
2. Domains over the canvases: `~/originba_dbt/jaspersoft/domains/<target>/` (generated; item ids from `~/originba_dbt/scripts/bi_names.py`).
3. Hand-built domains (CISADM joins, the active-8 snapshots): `domains/` with item ids from `output/domain_field_index.json`; `Domain Designs.xlsx` is their design record.
4. Clients, aliases, credential-family prefixes, DataSource names: `~/originba_dbt/clients.yml` (`config/clients.export.json` is its deploy copy).
5. The active snapshot set (eight tables) and its operations: `sql/performance/snapshots/` and its `docs/`.
6. CISADM semantics for SQL: `output/ai_cisadm_context.json`, `knowledge_base/c2m_cisadm/`; dialect and safety rules in `~/originba_dbt/.claude/skills/cisadm-sql/SKILL.md`.

## Operating References
0. `jaspersoft/README.md` (the delivery index) and `.claude/skills/` (the loadable skills)
1. `jaspersoft/docs/c2m_jaspersoft_delivery_playbook.md`
2. `knowledge_base/jaspersoft_artifact_model_and_performance.md`
3. `knowledge_base/jaspersoft_charts_visuals_jrs9.md`
4. `knowledge_base/jaspersoft_dynamic_features.md`

## Required Validation Before Done
1. JRXML XML parse succeeds.
2. No forbidden/fragile tags in chart blocks (`seriesColor`, misplaced `itemLabel`, bad order).
3. Domain query includes non-empty `<queryFields>`.
4. Input control JSON parses successfully.
5. README/docs updated when structure or behavior changes.
6. For Domain/Ad Hoc work, validate row grain and preserved population on a known slice before signoff.

## High-Risk Error Patterns To Avoid
1. `<filterExpression>` after `<group>`.
2. `<pageFooter>` after `<summary>`.
3. `<subDataset>` placed after fields/variables/bands.
4. Invalid chart child order and unsupported attributes (for 9.x).
5. Inner joins on optional enrichment tables that drop the driving population.
6. Raw Domain join graphs that multiply fact rows without a parity check.

## Preferred Delivery Style
1. Make concrete file changes.
2. Keep diffs small and reversible.
3. Archive uncertain legacy assets rather than hard-delete.
4. Keep root-level packaging artifacts out of the repo root; active manual import bundles live under `domains/exports/manual_imports/`; anything superseded goes to `archive/<date>/` with a row in its `INDEX.md` and a pointer at the old path.
