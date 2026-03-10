# Skill: Jaspersoft Derived Table Builder

## Goal
Prepare SQL for Jaspersoft Domain or Ad Hoc derived-table ingestion only when a derived table is the safest way to preserve grain, simplify the join graph, or expose a controlled semantic layer.

## Required References
- `docs/c2m_jaspersoft_delivery_playbook.md`
- `knowledge_base/jaspersoft_artifact_model_and_performance.md`
- `knowledge_base/jaspersoft_derived_table_rules.md`

## Steps
1. Confirm a derived table is actually needed; if raw Domain tables already preserve the grain cleanly, keep the Domain simple.
2. If a derived table is needed, fix one stable row grain in Oracle before exposing it to the Domain.
3. Ensure the SQL begins with `SELECT`, has no trailing semicolon, and avoids parser-fragile constructs unless verified in the target JRS setup.
4. Prefer exposing filterable fields over embedding parser-sensitive parameters.
5. Keep output fields stable, business-readable, and safe for report bindings, Topics, and Ad Hoc use.
6. Validate in Domain Designer; if parser errors occur, simplify the query shape further.
7. Compare derived-table row counts and control totals to the source Oracle SQL on a known validation slice.

## Output Contract
- Query parses in derived table editor.
- Supports report filters via dataset fields.
- No environment-specific hardcoded values unless intentionally scoped.
- Preserves the intended grain and row population on the validation slice.
