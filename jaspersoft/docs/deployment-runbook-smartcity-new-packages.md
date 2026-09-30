# SmartCity Deployment Runbook (New Packages)

This runbook follows the strict 9-step deployment sequence.
Packages covered:
- `deploy/ops_hub_dashboard_report_unit.zip`
- `deploy/client_value_scorecard_report_unit.zip`
- `deploy/collections_prioritization_report_unit.zip`

## 1. Pre-deployment verification
1. Confirm Jira/code review approval for SmartCity deployment.
2. Confirm target organization and source organization mapping.
3. Confirm build artifacts are current (timestamp/date).

## 2. Component enumeration
1. Enumerate all objects in deployment set:
- report units: Ops Hub, Client Value Scorecard, Collections Prioritization
- input controls and dependencies inside each zip
- datasource references impacted by import behavior

## 3. Export (exact flags)
1. Export changed objects only from source JRS.
2. Use exact export flags:
- Legacy Key
- Include repository permissions
- Include dependencies
- Include full resource path
3. Verify export zip contains only expected folders.

## 4. Backup target datasource
1. Backup target datasource in Temp folder.
2. Use naming format: `YYYY-MM-DD INITIALS`.

## 5. Backup target JRS objects
1. Backup target report units and related resources in Temp folder.
2. Use naming format: `YYYY-MM-DD INITIALS`.

## 6. Import extracted file (Update only)
1. Import using Legacy Key.
2. Import mode must be UPDATE only.
3. Verify import status is SUCCESS.

## 7. Re-import target datasource
1. Re-import original target datasource backup immediately after object import.
2. Confirm datasource credentials and URI are unchanged.

## 8. Run City Checker (SmartCity)
1. Validate organization-to-city mapping:
- Newark -> Newark
- Fond du Lac -> Fond du Lac
- Ellensburg -> Ellensburg
- College Station -> College Station
- CityCorp -> Russelville
2. Any mismatch is a security breach and blocks completion.

## 9. Smoke test and verify create dates
1. Verify Create Date is today for deployed objects.
2. Launch each report.
3. Execute with smoke parameters:
- `CLIENT_ID` as a valid division (or null-allowed where supported)
- `START_TS` and `END_TS` for recent production-safe window
4. Confirm PDF renders and KPI rows return.
