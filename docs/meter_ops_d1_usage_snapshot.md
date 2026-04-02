# Meter Ops Usage Header Snapshot

## Purpose
`CISADM.D1_USAGE_RPT_CURR` is the standardized usage-header snapshot for meter-side usage transactions.

It is designed for Jasper domains, ad hoc reporting, and analyst self-service where runtime joins across `D1_USAGE`, subscription context, quantity children, billing bridge tables, service agreement, account, and customer dimensions would otherwise be expensive and structurally fragile.

## Recommended workflow
1. Run the preflight validation in `sql/performance/meter_ops/d1_usage/00a_preflight_validation.sql`.
2. Confirm `D1_USAGE` is cleanly one row per `D1_USAGE_ID` and review the child-detail multiplicity.
3. Build the snapshot from the usage-header grain, not from a mixed-grain legacy domain export.
4. Run the validation suite after the table and procedure are created.

## Grain
One row per usage transaction in `CISADM.D1_USAGE`.

Natural key:
- `D1_USAGE_ID`

## Driving table
`CISADM.D1_USAGE`

This keeps the snapshot focused on usage-transaction truth rather than customer-first or scalar-detail-first reporting shapes.

## What is included
- usage status, reason, timing, calculation group, calculation type, source, route, cycle, and service-provider context
- usage-subscription context from `D1_US`
- estimate / skip / profile metadata from `CMS_D1_USAGE_BODA_VW`
- aggregated usage-period quantity context from `D1_USAGE_PERIOD_SQ`
- aggregated scalar-detail context from `D1_USAGE_SCALAR_DTL`
- optional billing bridge fields from `C1_USAGE`
- bill-segment, service-agreement, account, customer, and premise context when the billing bridge resolves

## What was intentionally removed
- raw `D1_USAGE_PERIOD_SQ` line grain
- raw `D1_USAGE_SCALAR_DTL` line grain
- hard-required billing or customer joins

Why:
- child detail is not the same business grain as a usage header
- the historical domains mixed those grains and risked both row multiplication and row loss
- users need a stable usage-header layer first, then separate child snapshots where determinant-level analysis is required

## Key design rule
Billing linkage is treated as optional enrichment, not as the driving truth.

That means the snapshot keeps all usage headers, then adds the best available `C1_USAGE` match through a conservative prioritized bridge path. If no bridge resolves, the usage header still remains in the snapshot.

## Best use cases
- usage transaction monitoring by status, reason, cycle, route, or service provider
- estimate and skip-pattern analysis
- comparing usage created vs. used-on-bill / linked-to-frozen-bseg behavior
- subscription-centric usage reporting
- high-level quantity analysis with one-row-per-usage preservation
- a governed header layer for future `D1_USAGE_PERIOD_SQ` or `D1_USAGE_SCALAR_DTL` child snapshots

## Business summary
This table answers a simple question:

"What usage transaction did the system create, what process and subscription context did it have, and how did it bridge into billing when that bridge exists?"

It gives end users a stable usage-header dataset without forcing them to understand the full C2M usage-processing and billing chain.
