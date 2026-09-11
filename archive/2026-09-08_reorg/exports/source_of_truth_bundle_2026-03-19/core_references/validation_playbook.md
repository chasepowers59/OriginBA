# Validation Playbook

## Goal
Verify report logic correctness across Oracle and Jaspersoft before client delivery.

## Standard Sequence
1. Data freshness check (latest event date by cycle).
2. Summary-vs-drilldown parity check.
3. Expected-vs-actual reconciliation reasonableness check.
4. Jasper parity check (DB output vs Jasper export).

## Required SQL Assets
- `sql/performance/bill_cycle/bill_cycle_active_validation.sql`
- `sql/performance/bill_cycle/bill_cycle_jaspersoft_parity_check.sql`
- `sql/performance/bill_cycle/bill_cycle_expected_vs_actual_reconciliation.sql`

## Pass Criteria
- Summary/drilldown parity deltas are zero.
- Most recent cycle flag behaves as expected.
- Expected vs actual gaps are explainable with event dates/schedule context.
- Jasper totals/fingerprint match DB control totals for same filter slice.

## Regression Triggers
Re-run full validation when:
- SQL logic changes in any of the three report datasets.
- Environment changes (DEV/QA/PROD).
- Status lookup behavior changes.
- Billing calendar/cycle setup changes.

## Signoff Checklist
- [ ] Query parses in Jaspersoft derived table editor.
- [ ] Output row counts match Oracle run.
- [ ] Sample account/SA drilldown rows match expected operational cases.
- [ ] Documentation updated for any logic change.
