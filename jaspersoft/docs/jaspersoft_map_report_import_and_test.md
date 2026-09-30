# Jaspersoft 9.0 Import and Test Guide (Origin_DEV / ORIGIN_DEV_DS)

This guide covers how to import and test the new map reporting package in:
- Jaspersoft Studio 9.0
- JasperReports Server 9.0

Scope assumptions:
- Source organization: `Origin_DEV`
- DEV datasource: `ORIGIN_DEV_DS`
- SQL source-of-truth: `output/workstream_reporting_dictionary.json` and `Domain Designs.xlsx`

## 1. Pre-checks
- Confirm all required files exist in repo:
  - `reports/map_meters_coverage.jrxml`
  - `reports/subreports/line_items_fieldwork.jrxml`
  - `sql/missing_meter_rollup.sql`
  - `sql/active_fieldwork.sql`
  - `server/input_controls/map_meters_input_controls.json`
  - `server/input_controls/map_meters_input_controls_rest.json`
  - `ci/smoke_insert_sample.sql`
  - `deploy/build_report_unit_map.sh`
  - `deploy/build_report_unit_map.ps1`
- Confirm no credentials are embedded in JRXML/SQL/JSON.

## 2. Jaspersoft Studio 9.0 Import and Local Validation
1. Open Studio 9.0.
2. Create or select Data Adapter named `ORIGIN_DEV_DS`.
3. Import JRXML:
   - `reports/map_meters_coverage.jrxml`
   - `reports/subreports/line_items_fieldwork.jrxml`
4. In `map_meters_coverage.jrxml`, confirm default adapter property points to `ORIGIN_DEV_DS`.
5. Validate parameters:
   - `CLIENT_ID` (String)
   - `START_TS` (Timestamp)
   - `END_TS` (Timestamp)
   - `THRESHOLD_HOURS` (Integer)
   - `REGION` (String)
   - `CLIENT_LOGO_URL` (String, hidden)
6. Compile both JRXMLs to `.jasper`.
7. Run Preview with sample values:
   - `CLIENT_ID=SMOKE_CITY_01`
   - `START_TS=2026-02-15 00:00:00`
   - `END_TS=2026-02-17 00:00:00`
   - `THRESHOLD_HOURS=24`
   - `REGION=NORTH`
8. Verify:
   - Report renders without SQL/JRXML errors.
   - Subreport returns active field work rows.

## 3. Oracle Read-Only SQL Validation
Run explain plans (read-only):
```sql
@sql/missing_meter_rollup.sql
@sql/active_fieldwork.sql
```

Inspect `DBMS_XPLAN.DISPLAY` for:
- bind usage (`:CLIENT_ID`, `:START_TS`, `:END_TS`, `:THRESHOLD_HOURS`, `:REGION`)
- partition pruning (if applicable)
- join method and cardinality reasonableness
- plan hash stability

## 4. Load Smoke Dataset in Staging (Non-Prod Only)
```sql
@ci/smoke_insert_sample.sql
```

Expected counts:
- `METERS=10`
- `METER_READINGS=1000`
- `FIELD_WORK_LOG=10`

## 5. Build Report Unit Package
Linux/macOS:
```bash
./deploy/build_report_unit_map.sh
```

Windows PowerShell:
```powershell
pwsh -File deploy/build_report_unit_map.ps1
```

Expected artifact:
- `deploy/map_meters_coverage_report_unit.zip`

## 6. JasperReports Server 9.0 Import (Origin_DEV)
1. Log into JRS 9.0 (NON-PROD first).
2. Confirm target org is `Origin_DEV`.
3. Import zip using required options:
   - Legacy Key
   - Include dependencies
   - Include repository permissions
   - Include full resource path
   - Update mode only
4. Confirm import status `SUCCESS`.
5. Re-check datasource binding on report unit:
   - DEV must use `ORIGIN_DEV_DS`.

## 7. Input Controls Setup Verification
Ensure controls exist and map correctly:
- `CLIENT_ID` (single select query)
- `START_TS` (datetime)
- `END_TS` (datetime)
- `THRESHOLD_HOURS` (number default 24)
- `REGION` (single select query)
- `CLIENT_LOGO_URL` (hidden text)

## 8. Server Smoke Test
Run report via REST:
```bash
curl -sS -u "${JRS_USER}:${JRS_PASSWORD}" \
  "${JRS_URL}/rest_v2/reports/organizations/Origin_DEV/reports/maps/map_meters_coverage.pdf?CLIENT_ID=SMOKE_CITY_01&START_TS=2026-02-15T00:00:00&END_TS=2026-02-17T00:00:00&THRESHOLD_HOURS=24&REGION=NORTH" \
  -o map_meters_coverage_smoke.pdf
```

Expected:
- HTTP 200
- non-empty PDF
- meter rows with stale/no-data logic
- subreport rows for `Assigned` and `In Progress`

## 9. Functional Acceptance Checklist
- SQL files execute with bind variables only.
- No hardcoded client IDs in production query logic.
- No cross-org datasource references.
- Report runs in Studio and Server.
- PDF render succeeds without memory issues for smoke sample.
- Create Date for imported resources is current deployment date.
