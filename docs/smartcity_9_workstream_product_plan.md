# SmartCity 9 Workstream Product Plan (Implementation-Ready)

Source of truth for SQL design and governance:
- `output/workstream_reporting_dictionary.json`
- `Domain Designs.xlsx` (metadata snapshot: `output/domain_designs_metadata.json`)

## Product Goal
Give municipalities a single, simpler experience in Jaspersoft:
1. one ops hub entry point
2. consistent parameters and filters
3. actionable KPI queues by workstream
4. strict data-quality and source-of-truth validation gates

## Implemented Artifacts
1. Ops Hub:
- `reports/ops_hub_dashboard.jrxml`
- `sql/smartcity_9_workstream_kpis.sql`
- `server/input_controls/ops_hub_dashboard_input_controls.json`
- `deploy/build_report_unit_ops_hub.sh`

2. Debt + Executive Packs:
- `reports/collections_prioritization.jrxml`
- `sql/collections_prioritization.sql`
- `reports/client_value_scorecard.jrxml`
- `sql/client_value_scorecard.sql`

3. Source-of-truth enforcement:
- `scripts/validate_source_of_truth_sql.py`
- CI integration in `ci/jrxml-smoke.yml`

## 9 Workstream Enhancements (Now Productized)
1. billing: open bill backlog KPI and cycle health trend.
2. cashiering: unresolved tender/deposit control exceptions.
3. meter_ops: install-event freshness indicator.
4. customer_ops: contact letter readiness defects.
5. new_services: stale pending service agreements.
6. finance: missing GL distribution status check.
7. common: inactive reference/lookup value monitor.
8. debt_mgmt: over-60 debt exposure and prioritized queue.
9. field_ops: service points without install-event linkage.

## Rollout Sequence (Municipal Clients)
1. Deploy Ops Hub to NON-PROD org.
2. Validate KPI behavior with one pilot municipality.
3. Promote with strict deployment compliance guide.
4. Add city-specific branding and policy text blocks.
5. Run weekly KPI review with operations + finance leads.
