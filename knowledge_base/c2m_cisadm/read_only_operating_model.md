# Read-Only Operating Model

## Scope
Applies to all utility reporting validations and SQL quality checks in this repository.

## Guardrails
1. Run `scripts/repo/sql_read_only_guard.py` before DB execution.
2. Run `00_read_only_preflight.sql` at the start of validation runs.
3. Use fail-fast parity gates (`08` and `09`) to stop on data differences.
4. Never run DDL/DML in validation packs.
5. Use explicit `ConnectString` parameters in runners; do not auto-load `.env` in validation/discovery workflows.

## Runtime Sequence
1. Read-only SQL guard
2. DB read-only privilege preflight
3. Original vs optimized result comparison
4. Sample-level consistency validation
5. Zero-diff assertions

## Read-Only Runners
- `scripts/performance/run_billed_usage_validation.ps1`
- `scripts/performance/run_cisadm_dictionary_discovery.ps1`
- `scripts/performance/run_sql_quality_workflow.ps1`

## Escalation Rule
If a test requires non-read-only activity, stop and request explicit user approval outside this workflow.
