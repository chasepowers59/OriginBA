# Skill: SQL Validation Guard

## Goal
Validate SQL and Jaspersoft changes before signoff so parity, preserved population, and freshness assumptions are explicit.

## Required References
- `docs/c2m_jaspersoft_delivery_playbook.md`
- `knowledge_base/jaspersoft_artifact_model_and_performance.md`
- `knowledge_base/validation_playbook.md`
- `knowledge_base/billing_cycle_reporting_semantics.md`

## Steps
1. Run freshness and parity checks in Oracle.
2. Run reconciliation checks for expected vs actual reasonableness.
3. Compare row counts before and after optional joins or derived-table shaping on a known slice.
4. Export Jasper output for the same filter slice and compare control totals/fingerprint.
5. Note whether the Jaspersoft result came from fresh query execution, Ad Hoc cache, or staged Topic data when that distinction matters.
6. Document mismatches and root cause (logic vs data window vs environment issue).
7. Update docs/KB if a new edge case is discovered.

## Output Contract
- Explicit PASS/FAIL status.
- Delta metrics documented when failed.
- Evidence query outputs captured for audit trail.
- Row-grain or preserved-population risks documented when present.
