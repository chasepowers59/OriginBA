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
