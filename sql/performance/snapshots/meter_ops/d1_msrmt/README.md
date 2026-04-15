# D1 Final Measurement Snapshot

## Purpose
This folder contains the snapshot build assets for `CISADM.D1_MSRMT_RPT_CURR`.

The snapshot preserves final processed measurement grain so measurement reporting does not rely on fragile runtime joins across `D1_MSRMT`, IMD lineage, measuring component, install event, and service point context.

## Grain
One row per processed measurement in `CISADM.D1_MSRMT`.

Natural key:
- `MEASR_COMP_ID`
- `MSRMT_DTTM`

## Domain XML
- Workspace copy: `D1_MSRMT_RPT_CURR_End_User_Friendly.xml`
- Import bundle: `domains/exports/manual_imports/D1_MSRMT_RPT_CURR_End_User_Friendly.xml`
- Keep both copies synchronized when the Domain changes.

## Master Guide
- Full technical guide: `06_master_technical_guide.md`
- Use it for final design, time-valid install-event logic, QA evidence, and deployment/debugging guidance.

## Implemented snapshot
- `00a_legacy_domain_preflight_validation.sql`
- `00_create_snapshot_table.sql`
- `01_refresh_snapshot_procedure.sql`
- `02_schedule_snapshot_job.sql`
- `03_validation_queries.sql`
- `04_intensive_qa_queries.sql`
- `05_qa_results_template.md`
- `06_master_technical_guide.md`
- `D1_MSRMT_RPT_CURR_End_User_Friendly.xml`
