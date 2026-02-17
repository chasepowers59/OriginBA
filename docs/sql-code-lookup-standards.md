# SQL Code Lookup Standards (_CD / _FLG)

This document defines how to resolve code values into business descriptions in C2M SQL/Jaspersoft reports.

## Source of Truth
Always align query design with:
1. `output/workstream_reporting_dictionary.json`
2. `Domain Designs.xlsx` (metadata snapshot: `output/domain_designs_metadata.json`)
3. Live schema verification in Oracle (`ALL_TABLES`, `ALL_TAB_COLUMNS`) for final join keys

## Lookup Resolution Rules
1. Prefer dedicated language lookup tables (`*_L`) when available.
2. Use `LANGUAGE_CD = 'EN'` for description joins unless a client-specific language is required.
3. Use `CI_LOOKUP_VAL` only when no dedicated lookup table exists.
4. For `CI_LOOKUP_VAL`, always use `TRIM` on both `FIELD_NAME` and `FIELD_VALUE` because values are padded.
5. Return both code and description columns:
- `<FIELD>_CD`
- `<FIELD>_DESCR`
For client-facing layouts, prefer rendering `<FIELD>_DESCR` only and fallback to code only when description is null.
6. If description is missing, fallback to code to prevent blank outputs.

## Canonical Mappings (Current Environment)
1. `COLL_CL_CD` -> `CISADM.CI_COLL_CL_L.DESCR`
2. `CC_CL_CD` -> `CISADM.CI_CC_CL_L.DESCR`
3. `CC_TYPE_CD` -> `CISADM.CI_CC_TYPE_L.DESCR` (join includes `CC_CL_CD`)
4. `ALERT_TYPE_CD` -> `CISADM.CI_ALERT_TYPE_L.DESCR80`
5. `TENDER_TYPE_CD` -> `CISADM.CI_TENDER_TYPE_L.DESCR`
6. `BSEG_STAT_FLG` -> `CISADM.CI_LOOKUP_VAL.VALUE_NAME` (`TRIM(FIELD_NAME)='BSEG_STAT_FLG'`)
7. `BILL_STAT_FLG` -> `CISADM.CI_LOOKUP_VAL.VALUE_NAME` (`TRIM(FIELD_NAME)='BILL_STAT_FLG'`)
8. `CONTACT_METH_FLG` -> `CISADM.CI_LOOKUP_VAL.VALUE_NAME` (`TRIM(FIELD_NAME)='CONTACT_METH_FLG'`)
9. `SA_STATUS_FLG` -> `CISADM.CI_LOOKUP_VAL.VALUE_NAME` (`TRIM(FIELD_NAME)='SA_STATUS_FLG'`)
10. `TNDR_STATUS_FLG` -> `CISADM.CI_LOOKUP_VAL.VALUE_NAME` (`TRIM(FIELD_NAME)='TNDR_STATUS_FLG'`)

## Reusable SQL Patterns
```sql
-- Dedicated lookup table pattern
LEFT JOIN CISADM.CI_COLL_CL_L COLL_L
  ON COLL_L.COLL_CL_CD = A.COLL_CL_CD
 AND COLL_L.LANGUAGE_CD = 'EN'
```

```sql
-- CI_LOOKUP_VAL pattern (padded values)
LEFT JOIN CISADM.CI_LOOKUP_VAL LU
  ON TRIM(LU.FIELD_NAME) = 'BSEG_STAT_FLG'
 AND TRIM(LU.FIELD_VALUE) = TRIM(S.BSEG_STAT_FLG)
```

## Governance Checks
1. Run `python scripts/build_cd_field_inventory.py` after SQL/JRXML edits.
2. Review `output/cd_field_inventory.json` for unmapped code fields.
3. Run `python scripts/validate_source_of_truth_sql.py` for changed SQL files.
4. Run `python -m pipeline.validate_tables` before packaging/deployment.
