# Assistant Skills Pack

This folder defines how report work should be executed in this repo.

## Files
- `domain_report_workflow.md`: end-to-end process for domain-based report delivery.
- `jrxml_schema_guardrails.md`: element-order and syntax rules to avoid Studio/JRS failures.
- `jrxml_expression_patterns.md`: reusable Jasper expression idioms from live reports.
- `cisadm_sql_prompt_guide.md`: structured prompt template for context-aware CISADM SQL generation.
- `deployment_compliance_checklist.md`: strict deployment steps and validations.
- `request_templates.md`: copy/paste prompts to request new reports or fixes.
- `skill_authoring_guide.md`: how to write high-quality reusable assistant skills.
- `past_mistakes_and_prevention.md`: known failure patterns and preventions.
- `report_preflight_checklist.md`: mandatory pre-completion checks.
- `troubleshooting_runbook.md`: exact remediation for recurring Studio/JRS errors.

## Usage
When requesting work, reference these files explicitly:
- "Follow `docs/assistant_skills/domain_report_workflow.md` and `docs/assistant_skills/jrxml_schema_guardrails.md`."

This keeps implementation consistent across reports and environments.
