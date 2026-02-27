# OriginBA Assistant Contract

## Objective
Build and maintain Oracle C2M + Jaspersoft Studio/Server reports using **Domain-first** design, production-safe conventions, and deployment compliance.

## Non-Negotiables
1. Prefer **Domain-based JRXML** (`language="domain"`) unless explicitly requested to use raw SQL.
2. Never embed credentials in JRXML/SQL/scripts.
3. Use datasource aliases only (`ORIGIN_DEV_DS`, `C2M_QA_DS`, `C2M_PROD_DS`).
4. Keep JRXML compatible with Jaspersoft Studio/Server 9.x schema ordering.
5. For any report change, also maintain matching input controls under `server/input_controls/`.
6. Preserve organization isolation (`Origin_DEV` source context by default).

## Source of Truth
1. `output/workstream_reporting_dictionary.json`
2. `Domain Designs.xlsx`
3. Exported Domain schema files (when provided)

## Required Validation Before Done
1. JRXML XML parse succeeds.
2. No forbidden/fragile tags in chart blocks (`seriesColor`, misplaced `itemLabel`, bad order).
3. Domain query includes non-empty `<queryFields>`.
4. Input control JSON parses successfully.
5. README/docs updated when structure or behavior changes.

## High-Risk Error Patterns To Avoid
1. `<filterExpression>` after `<group>`.
2. `<pageFooter>` after `<summary>`.
3. `<subDataset>` placed after fields/variables/bands.
4. Invalid chart child order and unsupported attributes (for 9.x).

## Preferred Delivery Style
1. Make concrete file changes.
2. Keep diffs small and reversible.
3. Archive uncertain legacy assets rather than hard-delete.
