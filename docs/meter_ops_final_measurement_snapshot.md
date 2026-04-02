# Meter Ops Final Measurement Snapshot

## Purpose
`CISADM.D1_MSRMT_RPT_CURR` is the standardized meter-operations snapshot for final processed measurements.

It is designed for ad hoc reporting tools, Jasper domains, and analyst self-service where runtime joins across measurement, measuring component, install event, service point, and IMD lineage would otherwise be expensive and fragile.

## Recommended workflow
1. Run the legacy preflight validation in `sql/performance/meter_ops/00a_legacy_domain_preflight_validation.sql`.
2. Confirm the legacy domain either preserves measurement grain or document exactly where it duplicates or drops rows.
3. Build the snapshot from the validated measurement-grain logic, not from the legacy XML alone.
4. Run the snapshot validation suite after the table and procedure are created.

## Grain
One row per processed measurement in `CISADM.D1_MSRMT`.

Natural key:
- `MEASR_COMP_ID`
- `MSRMT_DTTM`

## Driving table
`CISADM.D1_MSRMT`

This keeps the snapshot focused on final accepted measurement history rather than raw inbound IMD rows or field-activity process rows.

## What is included
- final measurement values and measurement timestamps
- measurement status, use, condition, and business object descriptions
- IMD lineage back to the original inbound read when available
- measuring component details, type, usage, latest-read metadata, and assigned user
- install-event context resolved as of the measurement timestamp
- service-point context, route/cycle, address, market, division, and lookup descriptions

## What was intentionally removed
- `D1_ACTIVITY` and related field-operations joins

Why:
- activity is a different workstream and not the same business grain as measurement
- the legacy domain mixed activity with measurement and created fan-out risk
- end users asked for a flexible measurement-centric ad hoc layer, not a field-activity process table

## Key design rule
Install-event context is joined by time validity, not by a hard-coded "current install only" assumption.

That means the snapshot tries to resolve the service point and install event that were valid when the measurement occurred, which is more appropriate for utility history than a simple current-state join.

## Best use cases
- final read history by component, service point, route, or cycle
- read-condition and measurement-use analysis
- IMD-to-measurement lineage review
- meter-operations dashboards and Jasper ad hoc views
- filtering and slicing by service-point attributes without runtime multi-join domain cost

## Business summary
This table answers a simple question: "What final measurement did the system store, and what meter/service-point context was in effect when that measurement happened?"

It gives end users a stable, measurement-grain dataset for meter-operations reporting without forcing them to understand the full C2M processing chain.
