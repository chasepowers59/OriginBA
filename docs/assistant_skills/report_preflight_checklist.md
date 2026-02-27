# Report Preflight Checklist (Before Marking Done)

## A) Domain and Query
1. Domain URI is correct for organization/workstream.
2. `queryString language="domain"` is set (if domain report).
3. `queryFields` is non-empty.
4. All `query.field.id` values exist in domain schema.

## B) JRXML Structure
1. `filterExpression` is before all `group` blocks.
2. `pageFooter` is before `summary`.
3. No invalid chart tags/attributes for Studio 9.x.
4. No external template dependency unless explicitly deployed.

## C) Parameters and Controls
1. Parameters use ALL_CAPS naming.
2. Input control JSON IDs match parameter names exactly.
3. Defaults are safe for first preview.
4. Null-safe filters for text/number/boolean.

## D) Validation Commands
1. XML parse JRXML.
2. JSON parse both input control files.
3. Smoke preview with minimal fields and no restrictive filters.

## E) Deployment Readiness
1. Datasource alias only (no credentials).
2. Organization-safe paths.
3. Dependencies enumerated.
4. Smoke render on server successful.
