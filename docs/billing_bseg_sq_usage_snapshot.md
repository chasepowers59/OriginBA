# Billing BSEG SQ Usage Snapshot

## Purpose
`CISADM.BSEG_SQ_USAGE_RPT_CURR` is the billing snapshot for trusted determinant-grain billed usage.

It is designed for ad hoc reporting where users need quantity analysis by `UOM`, `TOU`, and `SQI` without relying on `SA_TYPE` as a proxy for one unit family.

## Grain
One row per completed-bill determinant key:
- `BSEG_ID`
- `UOM_CD`
- `TOU_CD`
- `SQI_CD`

If multiple raw `CI_BSEG_SQ` rows share the same determinant key on the same segment, they are aggregated into one snapshot row.

## Driving tables
- `CISADM.CI_BSEG_SQ`
- `CISADM.CI_BSEG`
- `CISADM.CI_BILL`

## Why this grain was chosen
Testing showed that `SA_TYPE` is not a reliable unit family:
- some service types mix named units like `KWH`, `KW`, and `PF`
- many service types also include quantity rows with blank `UOM_CD`

That means quantity by `SA_TYPE` alone can be semantically misleading.

The determinant grain fixes that by keeping billed quantity attached to the actual `UOM` / `TOU` / `SQI` key that produced it.

## What is included
- determinant codes and descriptions from `CI_BSEG_SQ`
- trusted billed and initial usage quantities aggregated at determinant grain
- bill and bill-segment status, dates, IDs, and cycle context
- customer name at the account level
- service agreement type from `CI_SA`
- raw utility/service category code from `CI_SA_TYPE.SVC_TYPE_CD`
- account classification fields for slicing usage
- bill-segment flags and cancellation context

## What is intentionally excluded
- additive billed amount from `CI_BSEG_CALC`
- calc-line allocated amount
- aggregated read quantities from `CI_BSEG_READ`

Those measures were excluded because they are not the reporting truth for determinant-grain quantity analysis and would create a high risk of misuse or false reconciliation.

## Key design rule
`TOTAL_BILL_SQ` is the trusted additive measure in this snapshot.

It comes from `CI_BSEG_SQ` aggregated by determinant key, not from joining unrelated child tables or from trying to force billed dollars down to usage grain.

## Best use cases
- billed usage by `UOM`
- billed usage by `UOM` + `TOU`
- billed usage by `SQI`
- usage analysis by service type, bill cycle, customer class, or collection class
- identifying service types that combine multiple determinant families

## Business summary
This table answers the question: "What quantity was billed for each completed bill-segment determinant, and what billing context does that determinant belong to?"

It gives billing users a safe quantity-focused dataset for `UOM` analysis while leaving financially additive billed dollars at the segment grain where they remain trustworthy.
