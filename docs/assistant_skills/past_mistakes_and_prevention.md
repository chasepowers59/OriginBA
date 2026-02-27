# Past Mistakes and Prevention (Jaspersoft + Domain)

## 1) JRXML Element Order Violations
### Mistake
- `filterExpression` after `group`
- `pageFooter` after `summary`
- misplaced `subDataset`/`variable`

### Prevention
1. Follow `jrxml_schema_guardrails.md` order before saving.
2. Run XML parse check after every structural edit.
3. Keep chart and group changes isolated to small patches.

## 2) Chart Schema Errors
### Mistake
- Unsupported/invalid chart tags (`seriesColor`, misplaced `itemLabel`)
- Invalid attributes (`backgroundColor` on `<plot>`)

### Prevention
1. Use minimal chart blocks first.
2. Add formatting only after base chart compiles.
3. Avoid non-portable chart customizations unless tested in Studio 9.x.

## 3) Domain Query Errors
### Mistake
- `query.no.data` from empty `<queryFields>`
- wrong domain item IDs

### Prevention
1. Always verify `<queryField id="..."/>` from exported domain schema.
2. Re-open Dataset and Query and re-read fields after domain changes.
3. Test with 2-field smoke query before full report query.

## 4) Domain Cache Failures
### Mistake
- `CacheDatasetException: exception getting dataset from cache`

### Prevention
1. Test minimal domain query first.
2. Rebind domain adapter in Studio.
3. Clear/restart JRS cache path when server-side cache is stale.

## 5) Subreport Path Resolution
### Mistake
- Wrong `SUBREPORT_DIR` default and missing repository path alignment.

### Prevention
1. Use deployment-relative paths (`subreports/`) for report-unit packaging.
2. Verify subreport URI in JRS repository matches JRXML expression.

## 6) Template Dependency Breakage
### Mistake
- External style template not found at runtime.

### Prevention
1. Prefer inline styles for portability unless template is guaranteed deployed.
2. If using shared template, package and validate repository URI.
