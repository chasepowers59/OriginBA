# Snapshot Modernization Checklist

Use this checklist when converting an older manual Domain into a governed snapshot-backed Domain and moving reports onto it.

## 1. Legacy review
- Identify the old XML under `domains/working/manual_designs/`.
- Write down the business questions it answers.
- Confirm the real row grain.
- Identify the trusted additive measures.
- List the heavy joins, mixed-grain risks, and weak fields.
- Find the reports, dashboards, and Ad Hoc assets that depend on it.

## 2. Snapshot contract
- Choose the workstream.
- Choose the snapshot name.
- Define the natural key.
- Define the base population filter.
- Define which child overlays are optional only.
- Decide which old fields are required, optional, or trimmed.

## 3. SQL workspace
- Create `sql/performance/snapshots/<workstream>/<subset>/README.md`.
- Create `01_create_snapshot_table.sql`.
- Create `02_refresh_snapshot_procedure.sql`.
- Create `03_schedule_snapshot_job.sql`.
- Create `04_validation_queries.sql`.
- Add optional preflight or width-audit files if needed.

## 4. Database validation
- Run table DDL.
- Run procedure DDL.
- Execute the procedure manually.
- Confirm row count and `MAX(LOAD_DTTM)`.
- Confirm natural key uniqueness.
- Confirm required field population.
- Confirm child-field population only appears for the right subset.
- Confirm measures reconcile on a known slice.
- Review scheduler job definition and run history in SQL Developer.

## 5. Domain publication
- Create the importable XML under `domains/exports/manual_imports/`.
- Keep the new Domain pointed at the snapshot table, not the old runtime join graph.
- Preserve business-friendly names and folders where they help users.
- Do not carry duplicate or low-value legacy fields forward without a reason.
- Archive retired legacy XML variants intentionally if they still matter for rollback or lineage.

## 6. Report conversion
- Find reports using the old Domain or legacy field IDs.
- Repoint JRXML to the new Domain contract.
- Update matching JSON under `server/input_controls/`.
- Validate JRXML XML parse.
- Validate non-empty `<queryFields>`.
- Validate parameter names match input controls.
- Preserve or archive replaced legacy report assets when rollback would otherwise be unclear.

## 7. Documentation
- Add or update the snapshot business doc in `docs/`.
- Update `sql/performance/snapshots/docs/workstream_snapshot_catalog.md`.
- Update `sql/performance/snapshots/docs/snapshot_xml_inventory.md`.
- Update `sql/performance/snapshots/docs/business_question_snapshot_coverage.md` if coverage changed.
- Add SQL Developer operating guidance or confirm the snapshot is in `sql/performance/snapshots/docs/snapshot_sqldeveloper_runbook.md`.

## 8. DB impact and trim review
- Capture storage, counts, freshness, and scheduler health using `sql/performance/snapshots/impact/`.
- Review sparse or low-value columns with `05_snapshot_column_relevance.sql`.
- Record candidate columns for removal in the snapshot doc or impact notes.

## 9. Done
- Snapshot is governed, documented, validated, scheduled, and discoverable.
- New Domain XML is importable and documented.
- Dependent reports are migrated or explicitly listed as pending.
- Another analyst can inspect the table, procedure, and job in SQL Developer without asking for tribal knowledge.
