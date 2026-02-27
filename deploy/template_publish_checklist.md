# Template Publish Checklist (JRS 9.0)

## Scope
Use this checklist when publishing new report templates and derived reports.

## 1) Pre-publish
1. JRXML compiles in Studio (`.jasper` generation optional).
2. Parameters are named in `ALL_CAPS`.
3. SQL uses bind parameters and no hardcoded client IDs.
4. Subreport expressions use repository-safe paths (`repo:` preferred).

## 2) Resource Upload
1. Upload main report JRXML as report unit.
2. Upload required subreports under `subreports/` or `subreports/common/`.
3. Use resource IDs without file extensions.

## 3) Datasource Binding
1. Bind report to org datasource (`ORIGIN_DEV_DS` in DEV).
2. Confirm datasource is organization-scoped.
3. Confirm no cross-org datasource references.

## 4) Input Controls
1. Create controls for each required parameter.
2. Control parameter names match JRXML exactly.
3. Date/timestamp controls use date-time type.

## 5) Smoke Test
1. Execute report with known small test window.
2. Confirm at least one expected row or expected empty-state behavior.
3. Export PDF and verify render output.

## 6) Promotion Notes
1. Keep report code identical between orgs.
2. Only change datasource binding and org path.
3. Record report URI and datasource used in release notes.
