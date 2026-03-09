# C2M SQL Performance Playbook

## Baseline Checklist
- Capture runtime metrics: query msec, fetch msec, row count.
- Capture execution diagnostics using read-only methods available in your environment.
- Store baseline SQL text and bind values.

## Optimization Patterns
1. Early fact filtering
- Apply date/status filters in the first CTE or source subquery.

2. Pre-aggregation before fan-out joins
- Aggregate `D1_USAGE_SCALAR_DTL` to `D1_USAGE_ID` first.

3. Preserve business semantics
- Keep left joins where missing facts are meaningful.
- Do not remove status filters needed for business logic parity.

4. Reconcile before adoption
- Compare original vs optimized totals by business dimensions.
- Require zero differences for production acceptance.

## Evidence Required for Promotion
- Per-range comparison output (original_total vs optimized_total).
- Read-only execution diagnostics showing target access path improvements.
- Sample-level row checks for edge-case confidence.

## Repository Assets
- Billed usage validation scripts: `sql/performance/billed_usage/validation/`
- Bill cycle performance set: `sql/performance/bill_cycle/`
- Runtime launcher: `scripts/performance/run_billed_usage_validation.ps1`
