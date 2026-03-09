# C2M + Jaspersoft Professionalization Plan

## Objective
Build expert-level capability across Oracle Utilities C2M (CISADM schema), Jaspersoft domain/report design, SQL performance tuning, and analytics delivery.

## Phase 1 (Week 1-2): Foundation Hardening
- Standardize repository structure by function (domains, SQL performance, diagnostics, reconciliation, scripts).
- Validate source-of-truth SQL references with `scripts/validate_source_of_truth_sql.py`.
- Establish repeatable billed-usage optimization test pack under `sql/performance/billed_usage/validation/`.

## Phase 2 (Week 3-4): CISADM Domain Mastery
- Build and maintain table relationship maps for:
  - Account-to-SA: `CI_ACCT -> CI_SA`
  - Usage: `C1_USAGE -> D1_USAGE -> D1_USAGE_SCALAR_DTL`
  - Labels/lookups: `*_L` tables with `LANGUAGE_CD='ENG'`
- Create diagnostics for cardinality checks and duplicate-expansion hotspots.
- Add query-level test cases for business-safe join semantics (inner vs left outer).

## Phase 3 (Week 5-6): Performance Engineering
- Baseline high-volume reports (query msec, fetch msec, plan hash values).
- Apply optimization patterns:
  - Early filtering on fact tables (`D1_USAGE.START_DTTM`, statuses)
  - Pre-aggregation before fan-out joins
  - Deterministic reconciliation scripts (original vs optimized totals)
- Produce explain-plan evidence for every major optimization.

## Phase 4 (Week 7-8): Jaspersoft Excellence
- Domain-first design for new reports; SQL fallback only when justified.
- Enforce input-control parity for each report under `server/input_controls/`.
- Add deployment checklists and migration-safe packaging for DEV -> QA -> PROD.

## Ongoing Weekly Cadence
- Monday: backlog grooming (new reports + performance debt).
- Tuesday/Wednesday: implementation and unit validation.
- Thursday: parity/performance validation and explain-plan review.
- Friday: documentation updates and release packaging.

## Completion Criteria
- All critical report SQL categorized and validated.
- Billed-usage optimization scripts runnable end-to-end.
- Domain exports and working copies versioned and reproducible.
- Repeatable evidence trail for correctness and performance improvements.
