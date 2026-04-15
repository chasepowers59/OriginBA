# D1 Usage Header Snapshot

## Purpose
This folder is for the lean usage-header snapshot built from `CISADM.D1_USAGE`.

It exists because the legacy usage domains mixed header, child-detail, billing, and customer joins at runtime, which made row preservation fragile and obscured the real usage transaction grain.

## Grain
One row per usage transaction in `CISADM.D1_USAGE`.

Natural key:
- `D1_USAGE_ID`

## Use for
- usage transaction status and timing analysis
- used-on-bill and linked-to-frozen-bill-segment analysis
- subscription and calculation-group reporting
- estimate / skip behavior review
- bridging usage headers to `C1_USAGE`, `CI_BSEG`, `CI_SA`, account, and customer context
- customer class, service type, and premise segmentation of usage transactions

## Do not use for
- additive quantity reporting
- consumption by `UOM / TOU / SQI`
- measuring-component-level usage analysis
- full scalar-detail or period-SQ line analysis

Those belong in lower-grain child snapshots such as `D1_USAGE_SCALAR_DTL_RPT_CURR`.

## Key design rules
1. Drive from `D1_USAGE` so the snapshot preserves one row per usage header.
2. Keep `D1_USAGE_PERIOD_SQ` and `D1_USAGE_SCALAR_DTL` out of the header snapshot.
3. Keep the billing bridge optional.
4. Use a single canonical `C1_USAGE` bridge path (`D1_USAGE.USG_EXT_ID -> C1_USAGE.USAGE_ID` with `BO_STATUS_CD = 'BD-PROC'`) so billing enrichment stays useful without slowing the snapshot.
5. Keep customer/account/premise enrichment because those are common slice dimensions for usage operations.
6. Refresh the snapshot in monthly batches so large full-history loads do not exhaust Oracle TEMP.
7. Clear the snapshot with `DELETE` rather than `TRUNCATE` so refreshes are less likely to fail on `ORA-00054` when the table is being queried.

## Domain XML
- Workspace copy: `D1_USAGE_RPT_CURR_End_User_Friendly.xml`
- Import bundle: `domains/exports/manual_imports/D1_USAGE_RPT_CURR_End_User_Friendly.xml`
- Keep both copies synchronized when the Domain changes.
- Full technical guide: `08_master_technical_guide.md`

## Implemented snapshot
- `00a_preflight_validation.sql`
- `01_create_snapshot_table.sql`
- `02_refresh_snapshot_procedure.sql`
- `03_schedule_snapshot_job.sql`
- `04_validation_queries.sql`
- `05_status_cross_validation.sql`
- `06_intensive_qa_queries.sql`
- `07_qa_results_template.md`
- `08_master_technical_guide.md`
- `D1_USAGE_RPT_CURR_End_User_Friendly.xml`
