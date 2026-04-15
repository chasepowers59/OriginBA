# D1_MSRMT_RPT_CURR QA Results

## Run Metadata
- Environment: `DEV` (user-run in SQL Developer)
- Run date: `2026-04-13`
- Run by: User in SQL Developer; results documented in repo by Codex
- Snapshot object: `CISADM.D1_MSRMT_RPT_CURR`
- Validation SQL used:
  - `03_validation_queries.sql`
  - `04_intensive_qa_queries.sql`

## Summary
- Pass / Fail: `Pass`
- Ready for ad hoc use: `Yes`
- Key blockers: `None for measurement-grain parity or source row preservation`
- Residual risks:
  - `DIVISION_CD`, `MKT_CD`, and status-reason fields remain code-only by accepted business decision
  - the current install/service-point coverage QA query overstates source counts because it fans out `D1_MSRMT` through ungated install-event joins

## Population Boundary Decision
- Included measurements: `All rows from CISADM.D1_MSRMT`
- Excluded measurements: `None`
- Reason: `This snapshot is the governed final-measurement layer and is intended to preserve the full processed measurement population`

## Source Parity
- Source measurement count: `1,680,216`
- Snapshot measurement count: `1,680,216`
- Count difference: `0`
- Source rows missing in snapshot: `0`
- Snapshot rows not in source: `0`

## Install / Service Point Coverage
- Measuring component coverage result: `The QA source-side comparison is overstated by join fan-out and is not treated as a snapshot defect`
- Install event coverage result: `The QA source-side comparison is overstated by join fan-out and is not treated as a snapshot defect`
- Service point coverage result: `The QA source-side comparison is overstated by join fan-out and is not treated as a snapshot defect`
- Notes:
  - the top-level snapshot/source measurement parity and both anti-joins are exact, so the snapshot is not dropping measurement rows
  - the coverage block produced `1,711,246` source rows against `1,680,216` actual measurements, which proves the source-side query multiplied rows
  - the refresh procedure intentionally resolves install-event context with time-valid logic and a single chosen install event per measurement timestamp

## Raw-Code-Only Business Fields
- `DIVISION_CD` include with description?: `Keep as code-only; business translation not required for release`
- `MKT_CD` include with description?: `Keep as code-only; business translation not required for release`
- status reason codes include with description?: `Keep IMD, measuring-component, measurement, and service-point status reason codes as code-only; translation not required for release`
- Fields excluded from end-user surface: `None required for numeric acceptance`
- Reason for exclusion: `N/A`

## Utility / Business Context Decision Log
- Included measurement fields: `final measurement values, timestamps, status/use/condition fields, user-edited fields, reading values, and IMD lineage`
- Included install/SP context: `measuring component, time-valid install event, service point, route/cycle, address, market, and division context`
- Excluded activity/process context: `D1_ACTIVITY and related field-operations joins remain intentionally out of scope`
- Schema features not used in this tenant: `translated descriptions for DIVISION_CD, MKT_CD, IMD_BO_STATUS_REASON_CD, MC_BO_STATUS_REASON_CD, MSRMT_BO_STATUS_REASON_CD, and SP_BO_STATUS_REASON_CD are not maintained in the current release shape`
- Action taken on unused features: `accept those fields as code-only and do not block release on missing description columns`

## Final Decision
- Promote as-is: `Yes`
- Needs lookup additions: `No; accepted code-only fields can remain as-is`
- Needs population change: `No`
- Needs documentation update: `Completed; master technical guide added for this snapshot`
