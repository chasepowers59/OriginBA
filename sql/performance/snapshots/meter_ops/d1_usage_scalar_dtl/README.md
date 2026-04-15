# D1 Usage Scalar Detail Snapshot

## Purpose
This folder is for the scalar-detail usage snapshot built from `CISADM.D1_USAGE_SCALAR_DTL`.

It exists because quantity by `UOM / TOU / SQI`, customer class, premise, and measuring component is a different fact than a usage header and should not be forced into `D1_USAGE_RPT_CURR`.

## Grain
One row per scalar detail line in `CISADM.D1_USAGE_SCALAR_DTL`.

Natural key:
- `D1_USAGE_ID`
- `SEQ_NUM`

## Use for
- quantity and final quantity analysis by `UOM / TOU / SQI`
- customer class, service type, and premise consumption reporting
- measuring component and service point usage breakdowns
- raw vs. final usage comparison
- billing-linked scalar trace analysis

## Do not use for
- one-row-per-usage transaction counts
- usage-process monitoring without detail context

Use `D1_USAGE_RPT_CURR` for the header/process view.

## Key design rules
1. Drive from `D1_USAGE_SCALAR_DTL` joined to a monthly `D1_USAGE` batch.
2. Keep one row per scalar detail sequence.
3. Bring usage-header, subscription, billing, SA/account/customer, and premise context onto each scalar row.
4. Keep the `C1_USAGE` bridge optional and limited to the canonical billing path (`D1_USAGE.USG_EXT_ID -> C1_USAGE.USAGE_ID`, `BO_STATUS_CD = 'BD-PROC'`).
5. Refresh in monthly batches so full-history rebuilds are practical.

## Domain XML
- Workspace copy: `D1_USAGE_SCALAR_DTL_RPT_CURR_End_User_Friendly.xml`
- Import bundle: `domains/exports/manual_imports/D1_USAGE_SCALAR_DTL_RPT_CURR_End_User_Friendly.xml`
- Keep both copies synchronized when the Domain changes.

## Master Guide
- Full technical guide: `07_master_technical_guide.md`
- Use it for final design, refresh behavior, QA evidence, and deployment/debugging guidance.

## Implemented snapshot
- `01_create_snapshot_table.sql`
- `02_refresh_snapshot_procedure.sql`
- `03_schedule_snapshot_job.sql`
- `04_validation_queries.sql`
- `05_intensive_qa_queries.sql`
- `06_qa_results_template.md`
- `07_master_technical_guide.md`
- `D1_USAGE_SCALAR_DTL_RPT_CURR_End_User_Friendly.xml`
