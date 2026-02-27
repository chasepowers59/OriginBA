# Skill: Jaspersoft Derived Table Builder

## When to Use
Use when preparing SQL for Jaspersoft Domain/Ad Hoc derived table ingestion.

## Required References
- `knowledge_base/jaspersoft_derived_table_rules.md`

## Steps
1. Ensure SQL begins with `SELECT`.
2. Remove trailing semicolon.
3. Avoid parser-fragile constructs unless verified in target JRS setup.
4. Prefer exposing filterable fields over embedding parser-sensitive parameters.
5. Validate in Domain editor; if parser errors occur, simplify query shape.
6. Keep output fields stable for report bindings.

## Output Contract
- Query parses in derived table editor.
- Supports report filters via dataset fields.
- No environment-specific hardcoded values unless intentionally scoped.
