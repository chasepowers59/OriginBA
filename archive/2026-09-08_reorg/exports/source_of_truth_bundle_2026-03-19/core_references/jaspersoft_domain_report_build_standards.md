# Jaspersoft Domain Report Build Standards (Studio 9 / JRS 9)

Purpose:
- Prevent repeat errors while building C2M reports.
- Standardize styling, domain query patterns, and deployment-safe report design.

Scope:
- Jaspersoft Studio 9.0.x
- JasperReports Server (JRS) 9
- Domain-first reporting for SmartCity orgs (Origin_DEV pattern)

## 1) Key Takeaways From Recent Fixes

1. Use domain item IDs in domain queries, not table-qualified IDs.
- Use: `D1_SP_ID`, `CITY`, `DESCR_1`
- Avoid in `<queryField>`: `D1_SP.D1_SP_ID`, `F1_BUS_OBJ_STATUS_L.DESCR`

2. Use `language="domain"` query syntax with `queryFields/queryField`.
- Working structure:
```xml
<queryString language="domain"><![CDATA[
<query>
  <queryFields>
    <queryField id="D1_SP_ID"/>
  </queryFields>
</query>
]]></queryString>
```

3. Top-level JRXML element order is strict.
- Correct order:
  1) properties/styles
  2) `subDataset`
  3) `parameter`
  4) `queryString`
  5) `field`
  6) `variable`
  7) `filterExpression`
  8) `group`
  9) bands (`background/title/.../summary/noData`)

4. Domain URI in Studio should usually be org-relative.
- Use: `/SmartCity/Report/.../Field_Activity___Domain`
- Not: `/organizations/organization_1/organizations/Origin_DEV/...` (can 404 in org-scoped sessions)

5. Studio preview for map + domain subDataset can fail even when server works.
- Use `ENABLE_MAP_COMPONENT=false` by default in Studio.
- Enable map in server runs.

6. Don’t hardcode credentials in JRXML.
- Use server-managed datasource/domain resources only.

## 2) Recommended Build Pattern

1. Start from a known-good Studio-generated domain template.
2. Add domain properties:
- `ireport.domainUri`
- `com.jaspersoft.jrs.data.source`
- `com.jaspersoft.studio.data.defaultdataadapter`
3. Add fields from domain item IDs (source: exported `schema.data`).
4. Add minimal filter first (`D1_SP_ID != null`), then incrementally add business filters.
5. For maps:
- keep map optional via `ENABLE_MAP_COMPONENT` parameter.
- separate map marker dataset from KPI/detail logic if needed.

## 3) Styling Standard (Blue Theme)

Use shared styles in each report:
- `Base`
- `TitleBlue`
- `MetaBlue`
- `HeaderBlue`
- `DetailText`
- `SummaryBlue`

Design guidance:
- Dark blue title/header band (`#0A4A8A`)
- White header labels
- Light blue summary background (`#EAF3FF`)
- Avoid default unstyled text for client-facing outputs

## 4) Input Controls Standard

For domain reports:
- Prefer text/date/number/boolean controls over SQL query-based controls unless required.
- Match parameter names exactly.
- Keep optional controls non-mandatory for first-run validation.

Map report control:
- `ENABLE_MAP_COMPONENT` boolean
  - `false`: Studio-safe preview
  - `true`: server map render

## 5) Adapter and Execution Rules

1. `language="domain"` reports:
- Use JRS Server Domain adapter in Studio.
- JDBC adapter is for SQL reports, not domain query execution.

2. `language="SQL"` reports:
- Local JDBC adapter is valid for dev/testing.

3. If Studio fails but server works:
- treat as Studio execution-path issue, not necessarily datasource failure.

## 6) Common Errors and Fixes

1. `cvc-complex-type.2.4.a ... subDataset`
- Cause: `subDataset` placed after `parameter`.
- Fix: move top-level `subDataset` above top-level `parameter`.

2. `cvc-complex-type.2.4.a ... variable`
- Cause: `variable` after `group` or after title bands.
- Fix: place `variable` before `group` and before bands.

3. `resource.not.found` domain path
- Cause: wrong domain URI path in org context.
- Fix: use exact repository URI from Repository Explorer; prefer org-relative path in Studio.

4. `query.no.data`
- Cause: domain query XML format/fields not recognized.
- Fix: use `queryFields/queryField` and valid domain item IDs.

5. `Can not read domain` / DomainQueryExecuter NPE
- Cause: Studio map + domain subDataset execution path issue.
- Fix: keep map disabled in Studio (`ENABLE_MAP_COMPONENT=false`), validate map on server.

## 7) Pre-Commit Checklist (Required)

1. JRXML is XML well-formed.
2. Top-level element order validated.
3. Domain query uses domain item IDs only.
4. No credentials in report files.
5. Input controls JSON valid and parameter names match JRXML.
6. Studio validation run completed.
7. Server smoke run completed (at least one successful render).

## 8) Operational Reporting Value Pattern

For field operations reports, always include:
- Pain flag
- Recommended action
- Queue prioritization signal (age/severity)
- Summary KPIs for standup
- Geospatial readiness signal (geo missing vs geocoded)

This avoids “pretty but non-actionable” reports.
