# Request Templates

## New Domain Report
Use this request:

```text
Create a new domain-based JRXML report.
Domain URI: <uri>
Report path: reports/<name>.jrxml
Input controls path: server/input_controls/<name>_input_controls.json and _rest.json
Business goal: <goal>
Key metrics: <metric1>, <metric2>
Required filters: <filters>
Follow:
- docs/assistant_skills/domain_report_workflow.md
- docs/assistant_skills/jrxml_schema_guardrails.md
```

## Fix Existing JRXML
```text
Fix reports/<name>.jrxml.
Issue: <paste error>
Constraints:
- Keep domain-based query
- No subreports unless requested
- Studio/Server 9.x schema safe
Also update matching input controls if parameters changed.
Follow:
- skills/jrxml_report_builder/SKILL.md
- docs/assistant_skills/jrxml_schema_guardrails.md
- docs/assistant_skills/jrxml_expression_patterns.md
Run: python3 scripts/validate_jrxml_schema.py reports/<name>.jrxml
```

## Context-Aware CISADM SQL
```text
Workstream: <workstream>
Client: demo|qa|prod
Business question: <question>
Expected grain: <grain>
Validation slice: <counts or date range>
Follow:
- output/ai_cisadm_context.json
- skills/sql_report_builder/SKILL.md
- docs/assistant_skills/cisadm_sql_prompt_guide.md
Constraints: read-only SELECT, LEFT JOIN enrichment, no credentials
```

## Cleanup Pass
```text
Run safe cleanup.
Rules:
- Remove temp/cache/generated artifacts.
- Archive uncertain legacy files under archive/YYYY-MM-DD/.
- Update README/docs for moved/removed assets.
- Do not remove active deploy/CI referenced files.
```
