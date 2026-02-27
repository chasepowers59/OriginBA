# Field Activity Domain Map Report - Studio/Server 9 Test Guide

Report file:
- `reports/map_meters_coverage.jrxml`

Required server resources:
- Domain: `/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Field_Operations/Field_Activity/Field_Activity___Domain`
- Datasource: `ORIGIN_DEV_DS`

## 1) Studio 9 validation
1. Open `reports/map_meters_coverage.jrxml` in Jaspersoft Studio 9.
2. Use `Validate` in Studio (or open XML tab and confirm no schema error markers).
3. Compile report (`Build Report`) and confirm no compile errors.
4. Optional preview in Studio:
   - If preview is empty, that is expected unless Studio is connected to the same domain-backed dataset/query context.
   - The hard validation target is server execution with the domain report unit.

## 2) Server 9 publish/import
1. In JRS, create report unit at:
   - `/organizations/organization_1/organizations/Origin_DEV/SmartCity/Report/Workstreams/Field_Operations/Field_Activity/map_meters_coverage`
2. Upload `map_meters_coverage.jrxml`.
3. Set data source to the Field Activity Domain above (not raw JDBC query resources).
4. Create input controls using:
   - `server/input_controls/map_meters_input_controls.json`
   - or `server/input_controls/map_meters_input_controls_rest.json`
5. Run with blank filters first, then test with:
   - `REGION`
   - `START_TS` + `END_TS`
   - `ENABLE_MAP_COMPONENT`

## 3) Expected result
- Report opens without JRXML parse/XSD errors.
- Table rows render using domain fields (`D1_ACTIVITY_ID`, `D1_SP_ID`, `D1_GEO_LAT`, `D1_GEO_LONG`, etc.).
- Summary section shows record counters.
- No subreport path or JDBC SQL dependency errors.
- For Studio preview stability, keep `ENABLE_MAP_COMPONENT=false`.
- For server map rendering, set `ENABLE_MAP_COMPONENT=true`.

## 4) If you still see errors
- `cvc-complex-type.2.4.a`: JRXML element order issue; re-open current file from repo and republish.
- `Resource not found`: check report unit location and dependent resource URIs.
- Empty result: domain permissions/filtering may exclude rows for your user/org.
