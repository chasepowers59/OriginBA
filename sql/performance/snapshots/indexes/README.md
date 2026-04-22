# Snapshot Index Registry

## Purpose
This folder is the governed place to keep snapshot-table indexes that are either:
- actively adopted in the current environment
- approved as the next planned candidate to test or deploy

These are indexes on snapshot tables such as:
- `FT_GL_DISTRIBUTION_RPT_CURR`
- `FT_RPT_CURR`

They are not source-system DBA index requests on base Oracle tables.

## Files
- `01_active_snapshot_indexes.sql`: indexes currently accepted for use on snapshot tables
- `02_planned_snapshot_indexes.sql`: next approved candidate indexes that are not yet adopted
- `index_status.md`: plain-English status tracker for active and planned snapshot indexes

## Operating rule
- Add an index to `01_active_snapshot_indexes.sql` only after you have decided to keep it.
- Keep not-yet-adopted ideas in `02_planned_snapshot_indexes.sql`.
- Update `index_status.md` when the status changes.
