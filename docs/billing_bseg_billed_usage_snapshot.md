# Billing BSEG Billed Usage Snapshot

## Purpose
`CISADM.BSEG_BILLED_USAGE_RPT_CURR` is the billing snapshot for trusted bill-segment-level billed usage.

It is designed for ad hoc reporting where users need one row per bill segment and want billed usage from `CI_BSEG_SQ` without multiplying the results by also joining reads and calc headers directly.

## Grain
One row per `CI_BSEG.BSEG_ID` for completed bills.

Natural key:
- `BSEG_ID`

## Driving tables
- `CISADM.CI_BSEG`
- `CISADM.CI_BILL`

Child detail is aggregated before joining:
- `CI_BSEG_SQ` aggregated to segment
- `CI_BSEG_READ` aggregated to segment
- `CI_BSEG_CALC` aggregated to segment

## Why this grain was chosen
The legacy XML multiplies bill segments badly:
- completed `BSEG` rows: `2,214,870`
- legacy joined row count: `12,408,722`
- legacy distinct `BSEG` count after inner joins: `622,918`

It also inflates billed usage:
- direct `BILL_SQ` total: about `3.309E+10`
- duplicated `BILL_SQ` after legacy join: about `1.760E+11`

That means the XML cannot be trusted as a billed-usage fact source without aggregation first.

## What is included
- bill and bill-segment status, dates, IDs, and cycle context
- customer name at the account level
- service agreement type from `CI_SA`
- raw utility/service category code from `CI_SA_TYPE.SVC_TYPE_CD`
- account classification fields for slicing billed usage
- aggregated billed usage from `CI_BSEG_SQ`
- aggregated read context from `CI_BSEG_READ`
- aggregated billed amount from `CI_BSEG_CALC`
- single-determinant UOM / TOU / SQI only when the segment has exactly one determinant combination

## Key design rule
`TOTAL_BILL_SQ` is the trusted billed-usage measure at segment grain.

It comes from `CI_BSEG_SQ` aggregated by `BSEG_ID`, not from directly joining `CI_BSEG_SQ`, `CI_BSEG_READ`, and `CI_BSEG_CALC` in one rowset.

`TOTAL_CALC_AMT` is the rolled-up calculation amount from `CI_BSEG_CALC` and is the best available segment-level billed-amount proxy in this domain shape.

## Best use cases
- billed usage by bill segment
- billed usage and billed amount by raw utility/service category code
- billed usage by bill cycle, customer class, or collection class
- identifying segments with multiple determinant combinations
- segment-level reconciliation of billed quantity versus calculated amount

## Business summary
This table answers the question: "For each completed bill segment, how much usage was actually billed and what billing context does that segment belong to?"

It gives billing users a safe one-row-per-segment dataset and avoids the quantity inflation caused by the legacy multi-child domain joins.

`SA_TYPE_CD` / `SA_TYPE_DESC` provide the service type for the billed segment through `CI_BSEG.SA_ID -> CI_SA`.

`UTILITY_TYPE_CD` is the raw `CI_SA_TYPE.SVC_TYPE_CD` value. It is kept as source data for slicing, but it should not be treated as a standardized cross-client utility description without client-specific validation. `CUSTOMER_NAME` provides the primary account-holder name when available.
