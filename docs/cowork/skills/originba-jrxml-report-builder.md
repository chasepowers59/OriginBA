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

- `skills/jrxml_report_builder/SKILL.md`
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
