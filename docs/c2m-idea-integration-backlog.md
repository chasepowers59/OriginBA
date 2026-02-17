# C2M Utility Ideas: Integration Backlog

## Objective
Convert ideas into repeatable client value with governed SQL, Jaspersoft templates, and deployment-safe packaging.

## Priority 1 (Now)
1. Customer Contact Letter Readiness
- Assets: `sql/customer_contact_readiness_kpi.sql`, `reports/customer_contact_letter.jrxml`
- Value: improves first-pass print success and reduces manual rework.
- Rollout: weekly KPI + defect queue to customer operations.

2. Client Value Scorecard
- Assets: `sql/client_value_scorecard.sql`, `reports/client_value_scorecard.jrxml`
- Value: single-page executive view of debt, billing, payments, and printability quality.
- Rollout: monthly leadership packet and weekly ops standup.
- Packaging: `deploy/build_report_unit_scorecard.sh`

3. Collections Prioritization
- Assets: `sql/collections_prioritization.sql`, `reports/collections_prioritization.jrxml`
- Value: target highest-risk debt first and reduce aging backlog.
- Rollout: export top-N accounts daily to collections workflow.
- Packaging: `deploy/build_report_unit_collections.sh`

## Priority 2 (Next)
1. Cashiering Integrity Exception Queue
- Assets: `sql/c2m_business_use_cases.sql` (Use Case 3), `sql/deposit_reconciliation.sql`
- Integration: branch-level queue by tender source and status.

2. New Service Pipeline SLA Tracker
- Assets: `sql/c2m_business_use_cases.sql` (Use Case 2)
- Integration: pending SA aging alerts for operations supervisors.

3. Meter Ops Freshness Monitoring
- Assets: `sql/hourly_rollup.sql`, `output/workstream_health.json`
- Integration: flag stale install/read streams before billing cycles close.

## Enablement Pattern (Each Idea)
1. Validate SQL with bind variables and explain plan in DEV/QA.
2. Add/update Input Controls payload in `server/input_controls/`.
3. Create JRXML using ALL_CAPS parameters and no hardcoded datasource credentials.
4. Smoke-test render in JRS NON-PROD.
5. Promote using strict 9-step deployment sequence in `docs/deployment-compliance-guide.md`.
