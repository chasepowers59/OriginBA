# C2M Client Value Integration Plan

This plan turns current SQL/JRXML assets into recurring client value with clear rollout steps.
Source of truth remains:
- `output/workstream_reporting_dictionary.json`
- `Domain Designs.xlsx`

## Phase 1: Stabilize Data Trust (Week 1)
1. Enforce health checks before report release.
2. Track these KPIs per client org:
   - Billing gap count (`config_completeness.json`)
   - Contact letter readiness defects
   - Field/meter data currency risk
3. Gate new report promotions on:
   - read-only validation pass
   - explain plan review on large-table SQL

## Phase 2: Deploy High-Value Client Packs (Weeks 2-4)
1. Collections Pack
   - SQL: `sql/arrears_strategic.sql`, `sql/c2m_business_use_cases.sql` (Use Case 1)
   - Templates: arrears portfolio summary + account drilldown letter
   - Value: prioritizes collections workload by debt age and alerts
2. Cashiering Integrity Pack
   - SQL: `sql/deposit_reconciliation.sql`, `sql/duplicate_payment.sql`, `sql/c2m_business_use_cases.sql` (Use Case 3)
   - Templates: exception queue form + branch/day control summary
   - Value: reduces unreconciled tenders and close-day surprises
3. Customer Contact Letter Pack
   - SQL: `sql/customer_contact_letter.sql`, `sql/c2m_business_use_cases.sql` (Use Case 4)
   - Templates: regulatory notice, payment reminder, service communication
   - Value: printable customer communication with data quality guardrails
4. Meter Operations Pack
   - SQL: `sql/hourly_rollup.sql`
   - Templates: hourly consumption variance and install-event freshness dashboard
   - Value: detects read/installation issues before billing impact

## Phase 3: Operationalize in Jaspersoft (Weeks 4-6)
1. Standardize input controls:
   - `CLIENT_ID`, `START_TS`, `END_TS`, optional `ACCT_ID`
2. Use subreports for reusable blocks:
   - address block
   - payment summary table
   - legal footer/branding
3. Adopt template families for client branding:
   - Civic Classic
   - Utility Modern
   - Operations Compact
4. Add runtime metadata footer in each report:
   - run timestamp
   - datasource name
   - parameter echo for auditability

## Phase 4: Measure Business Impact (Ongoing)
1. Collections outcomes:
   - debt over 60 trend
   - promise-to-pay conversion rate
2. Cashiering outcomes:
   - unresolved tender exceptions
   - reconciliation turnaround time
3. Contact center outcomes:
   - successful letter generation rate
   - reduced rework from missing contact/address data
4. Metering outcomes:
   - stale install event count
   - read exception aging

## Integration Backlog (Next)
1. Add per-client scorecard report unit combining:
   - workstream health
   - configuration completeness
   - top corrective actions
2. Add CI check to run `pipeline.validate_tables` on PR for SQL/report changes.
3. Add report smoke render job for NON-PROD orgs using datasource aliases only.
