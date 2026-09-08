# CISADM Core Data Model (Reporting Focus)

## Primary Transaction Flow
1. `CI_ACCT` (account)
2. `CI_SA` (service agreement)
3. `C1_USAGE` (usage transaction envelope)
4. `D1_USAGE` (usage details/status)
5. `D1_USAGE_SCALAR_DTL` (scalar quantity detail)

## Key Join Patterns
- `CI_ACCT.ACCT_ID = CI_SA.ACCT_ID`
- `CI_SA.SA_ID = C1_USAGE.SA_ID`
- `C1_USAGE.USAGE_ID = D1_USAGE.USG_EXT_ID`
- `D1_USAGE.D1_USAGE_ID = D1_USAGE_SCALAR_DTL.D1_USAGE_ID`

## High-Value Status Filters
- `C1_USAGE.BO_STATUS_CD = 'BD-PROC'`
- `D1_USAGE.BO_STATUS_CD = 'SENT'`
- Service agreement active filters depend on business context (often `SA_STATUS_FLG='20'`).

## Lookup Enrichment Pattern
Use language-specific label tables with `LANGUAGE_CD='ENG'`, e.g.:
- `CI_CUST_CL_L`
- `CI_LOOKUP_VAL_L`
- `D1_USG_CAL_TYPE_L`
- `F1_BUS_OBJ_STATUS_L`

## Performance Risk Areas
- Joining `D1_USAGE_SCALAR_DTL` at detail grain before aggregation.
- Late filtering on `D1_USAGE.START_DTTM` and status columns.
- Joining multiple lookup tables before reducing fact row counts.

## Recommended Reporting Pattern
- Filter `D1_USAGE` early.
- Aggregate scalar detail per `D1_USAGE_ID` before joining to account/SA dimensions.
- Keep LEFT OUTER semantics where missing scalar rows must still return usage rows.
