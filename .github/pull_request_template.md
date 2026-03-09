## Summary
- Describe the SQL/report/domain change and business reason.

## Required Checks (SQL Governance)
- [ ] I ran `pwsh -File scripts/repo/pre_merge_sql_gate.ps1` and all static gates passed.
- [ ] For changes in governed SQL folders, read-only guard is clean.
- [ ] For changes in governed SQL folders, source-of-truth table validation is clean.
- [ ] I did not add DDL/DML/admin mutations to validation or diagnostics SQL.

## Read-Only DB Validation (when applicable)
- [ ] I ran read-only DB checks with explicit connect string (no `.env` auto-load).
- [ ] I attached or summarized parity/performance evidence for affected workloads.

## Notes
- Include assumptions, known limitations, and follow-up tasks.
