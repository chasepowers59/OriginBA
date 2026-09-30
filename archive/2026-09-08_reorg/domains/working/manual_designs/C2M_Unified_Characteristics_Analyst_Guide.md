# C2M Unified Characteristics Domain - Analyst Guide

## Domain purpose

This domain unifies raw characteristic rows for five core C2M object families:

- Person (`CI_PER_CHAR`)
- Account (`CI_ACCT_CHAR`)
- Service Agreement (`CI_SA_CHAR`)
- Premise (`CI_PREM_CHAR`)
- Service Point (`D1_SP_CHAR`)

Characteristic type descriptions are decoded from `CI_CHAR_TYPE_L` with `LANGUAGE_CD = 'ENG'`.

## Grain contract (critical)

This domain is **characteristic-row grain**, not base-object grain.

Canonical row identity:

- `OBJECT_TYPE`
- `OBJECT_ID`
- `CHAR_TYPE_CD`
- `CHAR_EFFDT`

Equivalent composite key in this design:

- `CHAR_ROW_KEY = OBJECT_ID || '|' || CHAR_TYPE_CD || '|' || CHAR_EFFDT`

## How to aggregate safely

Use these defaults:

- Base-object populations: `CountDistinct(OBJECT_ID)` grouped by `OBJECT_TYPE`
- Characteristic coverage: `CountDistinct(CHAR_TYPE_CD)`
- Characteristic row volume: `CountDistinct(CHAR_ROW_KEY)`

Avoid:

- plain `Count(OBJECT_ID)` when comparing person/account/SA/SP/premise populations
- summing unrelated numeric fields across mixed `OBJECT_TYPE` values

## Recommended filter defaults

For consistent analysis and to reduce accidental fan-out misreads:

1. Filter to one `OBJECT_TYPE` first.
2. Then filter/select `CHAR_TYPE_CD` as needed.
3. Use `CHAR_TYPE_DESCR` only as a presentation field (keep `CHAR_TYPE_CD` in the view for traceability).

## Join behavior summary

- Characteristic spine is preserved with left joins.
- Object context (person/account/SA/SP/premise) is enrichment only.
- Decode enrichment:
  - `CI_CHAR_TYPE_L` on `CHAR_TYPE_CD` and `LANGUAGE_CD = 'ENG'`

If decode is missing, the raw code still remains available in `CHAR_TYPE_CD`.

## QA checklist location

Run and attach results from:

- `domains/working/manual_designs/C2M_Unified_Characteristics_QA_Checklist.sql`

Minimum signoff evidence:

1. Source row count parity by object type.
2. Distinct object parity by object type.
3. Decode coverage rates (missing `CHAR_TYPE_DESCR` should be understood and documented).
