# D1 Usage Header Snapshot

## Purpose
This folder is for the usage-header snapshot built from `CISADM.D1_USAGE`.

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
- high-level usage quantity analysis from aggregated child detail

## Do not use for
- additive determinant-level quantity analysis by `UOM / TOU / SQI`
- full scalar-detail or period-SQ line analysis
- direct billed-dollar reporting

Those require lower-grain child snapshots or separate billing artifacts.

## Key design rules
1. Drive from `D1_USAGE` so the snapshot preserves one row per usage header.
2. Aggregate `D1_USAGE_PERIOD_SQ` and `D1_USAGE_SCALAR_DTL` before joining so child detail does not multiply the header.
3. Keep the billing bridge optional.
4. Use a prioritized one-row-per-usage `C1_USAGE` bridge so historical join ambiguity does not duplicate the snapshot.

## Implemented snapshot
- `00a_preflight_validation.sql`
- `01_create_snapshot_table.sql`
- `02_refresh_snapshot_procedure.sql`
- `03_schedule_snapshot_job.sql`
- `04_validation_queries.sql`
