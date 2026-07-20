# CMS Field Activity views (legacy Domain enrichment)

## Why this exists

Standard Offering **Field Activity** Domain expects these CISADM objects:

- `CMS_C1_REPRESENTATIVE_BODA_VW` — mobile-lite service area / capability from representative BO XML
- `CMS_D1_ACTIVITY_CHAR_VW` — pivoted FA status / priority / third-party rep chars
- `CMS_D1_ACTIVITY_D1FA_BODA_VW` — FA BO_DATA_AREA attributes (appointment, contact, pickup)

CityCorp had copies only under `CISADM290` (INVALID). `CISREAD` synonyms pointed at missing `CISADM` objects — same failure mode as `CMS_SA_SNAPSHOT`.

Domain Designer then warns that removing the datasource tables will delete these views and break `JoinTree_1`.

## Scripts

1. `01_create_cms_activity_views.sql` — create views, grants, CISREAD synonyms
2. `02_validate_cms_activity_views.sql` — status, counts, CISREAD access, join smoke

## CityCorp deploy

```bash
python3 scripts/local/run_client_oracle_sql.py --client citycorp \
  --file sql/performance/snapshots/field_ops/cms_activity_views/01_create_cms_activity_views.sql

python3 scripts/local/run_client_oracle_sql.py --client citycorp \
  --file sql/performance/snapshots/field_ops/cms_activity_views/02_validate_cms_activity_views.sql
```

## Notes

- These are **views**, not refreshable snapshot tables.
- Source truth is live `C1_REPRESENTATIVE` / `D1_ACTIVITY` / `D1_ACTIVITY_CHAR` (+ `D1_ACTIVITY_TYPE` for D1FA filter).
- Longer-term Field Ops reporting may use `FIELD_ACTIVITY_RPT_CURR`; these CMS views keep the live SO Domain working.
