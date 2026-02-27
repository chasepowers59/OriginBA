# Skill: SQL Validation Guard

## When to Use
Use before signoff/deployment for any SQL/Jaspersoft report change.

## Required References
- `knowledge_base/validation_playbook.md`
- `knowledge_base/billing_cycle_reporting_semantics.md`

## Steps
1. Run freshness and parity checks in Oracle.
2. Run reconciliation checks for expected vs actual reasonableness.
3. Export Jasper output for same filter slice and compare control totals/fingerprint.
4. Document mismatches and root cause (logic vs data window vs environment issue).
5. Update docs/KB if a new edge case is discovered.

## Output Contract
- Explicit PASS/FAIL status.
- Delta metrics documented when failed.
- Evidence query outputs captured for audit trail.
