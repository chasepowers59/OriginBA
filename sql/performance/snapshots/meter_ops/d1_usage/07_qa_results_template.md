# D1_USAGE_RPT_CURR QA Results

## Run Metadata
- Environment: `User-provided QA results`
- Run date: `2026-04-10`
- Run by: User; results documented in repo by Codex
- Snapshot object: `CISADM.D1_USAGE_RPT_CURR`
- Validation SQL used:
  - `04_validation_queries.sql`
  - `05_status_cross_validation.sql`
  - `06_intensive_qa_queries.sql`

## Summary
- Pass / Fail: `Pass for source parity, row preservation, and optional billing-bridge coverage`
- Ready for ad hoc use: `Yes`
- Key blockers: `None`
- Residual risks:
  - no population-loss risk was found in this QA run
  - no billing-bridge fan-out or row-loss signal was found in this QA run
  - `DIVISION_CD`, `BO_STATUS_REASON_CD`, and `US_BO_STATUS_REASON_CD` remain code-only by accepted design choice and may need future lookup enhancement if business semantics change

## Population Boundary Decision
- Included usage headers: `All D1_USAGE rows where NVL(START_DTTM, NVL(CRE_DTTM, STATUS_UPD_DTTM)) is not null`
- Excluded usage headers: `Only source rows with no usable timestamp in START_DTTM, CRE_DTTM, or STATUS_UPD_DTTM`
- Reason: `The refresh procedure batches by best available usage timestamp and intentionally preserves the D1_USAGE header grain`

## Source Parity
- Source usage count: `684,214`
- Snapshot usage count: `684,214`
- Count difference: `0`
- Source rows missing in snapshot: `0`
- Snapshot rows not in source: `0`

## Billing Bridge And Context Coverage
- `C1_USAGE` bridge coverage result: `Pass; 623,557 source rows and 623,557 snapshot rows resolved, diff 0`
- BSEG coverage result: `Pass; 623,366 source rows and 623,366 snapshot rows resolved, diff 0`
- SA coverage result: `Pass; 623,557 source rows and 623,557 snapshot rows resolved, diff 0`
- Account coverage result: `Pass; 623,557 source rows and 623,557 snapshot rows resolved, diff 0`
- Notes:
  - monthly parity matched exactly across all `36` returned usage months
  - sparse months at the edges of history also matched exactly, so batching logic did not introduce month-boundary loss
  - optional enrichment behaved as intended: unresolved billing context did not remove the driving usage header rows

## Raw-Code-Only Business Fields
- `DIVISION_CD` include with description?: `Keep as code-only for this release`
- status reason codes include with description?: `Keep as code-only for this release`
- Fields excluded from end-user surface: `None`
- Reason for exclusion: `N/A; the current release accepts these raw codes for traceability and operational use`

## Utility / Business Context Decision Log
- Included usage process fields:
  - usage header identifiers and timing
  - usage and subscription status/process context
  - cycle, route, service-provider, and bill-cycle context
- Included customer/billing fields:
  - optional `C1_USAGE` bridge fields
  - bill-segment, SA, account, customer, customer class, and premise context where the billing bridge resolves
- Excluded quantity/detail fields: `Usage scalar-detail and period-SQ quantity logic remain intentionally out of the header snapshot`
- Schema features not used in this tenant: `Readable translation columns for DIVISION_CD, BO_STATUS_REASON_CD, and US_BO_STATUS_REASON_CD are not yet implemented in this snapshot`
- Action taken on unused features: `Accepted for release as code-only fields; treat description columns as an optional future enhancement rather than a blocker`

## Final Decision
- Promote as-is: `Yes`
- Needs lookup additions: `Optional future enhancement only; not a release blocker`
- Needs population change: `No`
- Needs documentation update: `Completed in this QA results file`
