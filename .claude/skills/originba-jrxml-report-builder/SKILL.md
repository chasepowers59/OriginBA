---
name: originba-jrxml-report-builder
description: Create or fix Domain-first JRXML reports, input controls, and chart blocks for Jaspersoft Studio/Server 9.x.
---

# OriginBA JRXML Report Builder

## When to use

- Creating or editing JRXML under `reports/`
- Fixing compile/render errors in domain reports
- Adding or changing report parameters and input controls

## Required references

- the *JRXML report builder* section below
- `docs/assistant_skills/jrxml_schema_guardrails.md`
- `docs/assistant_skills/jrxml_expression_patterns.md`
- `docs/assistant_skills/domain_report_workflow.md`
- `docs/assistant_skills/troubleshooting_runbook.md`
- `output/domain_field_index.json`

## Steps

1. Map business fields to Domain item IDs from `output/domain_field_index.json`; never invent IDs.
2. Use `language="domain"` with non-empty `<queryFields>`.
3. Enforce element order: `filterExpression` before `group`; `pageFooter` before `summary`.
4. No `seriesColor`, invalid plot attributes, or misplaced `itemLabel` in charts.
5. Update both input control files:
   - `server/input_controls/<report>_input_controls.json`
   - `server/input_controls/<report>_input_controls_rest.json`
6. Keep JRXML parameter IDs aligned with input control IDs.
7. Validate before done:
   ```bash
   python3 scripts/validate_jrxml_schema.py reports/<name>.jrxml
   ```
8. On errors, follow `docs/assistant_skills/troubleshooting_runbook.md` and `past_mistakes_and_prevention.md`.

## Output contract

- XML parse passes
- Non-empty domain query fields with correct IDs
- Input control JSON parses
- No forbidden chart tags for 9.x

> **Style is Origin 2025** (`~/originba_dbt/.claude/skills/origin-doc-style/SKILL.md`: Aptos, Sapphire `#006FAC`); the Blue Theme in `jaspersoft/docs/jaspersoft_domain_report_build_standards.md` applies only when matching an EXISTING Standard Offering report family. `language="domain"` stays the query language (jasperQL is the 9.0 recommendation, not adopted).

## JRXML report builder (Jaspersoft 9.x)

*Folded from the *JRXML report builder* section below on 2026-09-08; the file is archived.*

### Goal
Create or fix domain-first JRXML reports and paired input controls with Studio/Server 9.x-safe structure, null-safe expressions, and deployment compliance.

### Inputs
- Business goal, metrics, and required filters.
- Target Domain URI and exported `schema.data` (or `output/domain_field_index.json`).
- Closest existing report pattern from `reports/`.
- Environment scope (`Origin_DEV` by default).

### Required References
- `AGENTS.md`
- `output/ai_cisadm_context.json` (when SQL/source-table context is needed upstream)
- `output/domain_field_index.json`
- `jaspersoft/docs/c2m_jaspersoft_delivery_playbook.md`
- `jaspersoft/docs/jaspersoft_domain_report_build_standards.md`
- `docs/assistant_skills/jrxml_schema_guardrails.md`
- `docs/assistant_skills/jrxml_expression_patterns.md`
- `docs/assistant_skills/domain_report_workflow.md`
- `docs/assistant_skills/past_mistakes_and_prevention.md`
- `docs/assistant_skills/troubleshooting_runbook.md`
- `knowledge_base/jaspersoft_charts_visuals_jrs9.md`

### Steps
1. Confirm artifact type with the *Domain modeling rules* section below (Report vs Domain vs Ad Hoc vs Dashboard).
2. Map business fields to Domain item IDs using `output/domain_field_index.json`; do not invent IDs.
3. Clone layout/styles from the closest existing report (for example `field_activity_operational_intelligence.jrxml` for filters and severity styling).
4. Build domain query with non-empty `<queryFields>` using exact item IDs from the Domain export.
5. Bind fields with `net.sf.jasperreports.query.field.id` properties matching Domain IDs.
6. Add null-safe `filterExpression`, KPI variables, and conditional styles using patterns from `jrxml_expression_patterns.md`.
7. Create or update both input control files under `server/input_controls/`:
   - `<report>_input_controls.json`
   - `<report>_input_controls_rest.json`
8. Keep parameter IDs in JRXML exactly aligned with input control IDs.
9. Run validation before done:
   - `python3 scripts/validate_jrxml_schema.py reports/<name>.jrxml`
   - JSON parse on both input control files
   - Studio/JRS smoke render when available

### Fix Compilation Errors Workflow
1. Paste the full stack trace and the smallest XML snippet that fails.
2. Check `docs/assistant_skills/troubleshooting_runbook.md` and `past_mistakes_and_prevention.md`.
3. Common fixes:
   - Move `filterExpression` before `group`
   - Move `pageFooter` before `summary`
   - Remove forbidden chart tags (`seriesColor`)
   - Repair Domain query field IDs / empty `<queryFields>`
   - Fix parameter/control ID mismatches

### Output Contract
- Domain-based JRXML unless raw SQL was explicitly requested.
- Datasource aliases only: `ORIGIN_DEV_DS`, `C2M_QA_DS`, `C2M_PROD_DS`.
- Matching dual input control JSON for every changed report.
- Validator passes for touched JRXML files.

### Do Not
- Embed credentials in JRXML or input controls.
- Use table-qualified Domain query field IDs (`D1_SP.D1_SP_ID`).
- Skip input control updates when parameters change.
- Ship JRXML without running `scripts/validate_jrxml_schema.py`.
