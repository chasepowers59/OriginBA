# Troubleshooting Runbook (Studio + JRS)

## Error: `query.no.data`
### Cause
Domain query has no selected fields.
### Fix
1. Open Dataset and Query.
2. Confirm domain URI.
3. Add at least 2 query fields.
4. Read fields/save/retry.

## Error: `CacheDatasetException`
### Cause
Server-side domain cache failure or stale metadata.
### Fix
1. Run a minimal 2-field smoke query.
2. Rebind domain adapter in Studio.
3. Restart JRS/Tomcat or clear server cache.
4. Re-run report with default/minimal parameters.

## Error: `cvc-complex-type...`
### Cause
JRXML element order/schema violation.
### Fix
1. Check ordering against `jrxml_schema_guardrails.md`.
2. Move `filterExpression` before `group`.
3. Move `pageFooter` before `summary`.
4. Remove invalid chart elements.

## Error: `Resource not found at subreports/...`
### Cause
Wrong subreport path or missing deployed resource.
### Fix
1. Align `SUBREPORT_DIR` with deployed structure.
2. Verify subreport URI exists in repository.
3. Re-import package with dependencies.

## Error: Oracle JDBC driver missing in Studio
### Cause
Driver not configured in local Studio adapter.
### Fix
1. Add Oracle JDBC jar to Studio data adapter.
2. Test connection in adapter.
3. Retry preview.

## Diagnostic Sequence (Always)
1. Minimal fields + minimal parameters.
2. Validate XML/JSON locally.
3. Re-expand query and visuals gradually.
