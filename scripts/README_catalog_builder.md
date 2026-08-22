# Where did build_dbt_reporting_catalog.py go?

Moved to **originba_dbt** as `scripts/build_portal_catalog.py` (2026-08-22).

It derives the portal catalog from that repo's dbt contracts
(`models/marts/reporting/_reporting.yml`) and column lineage
(`docs/column_lineage.json`). Living here, a contract change over there did not
touch this repo, so nothing prompted a regeneration and the API served stale
catalogs -- four times in one day. The generator now lives with what it reads.

It still reads this repo's question catalogue
(`apps/analytics-portal/src/lib/c2m-question-catalog.js`) and writes this repo's
`output/catalog_dbt.json`, locating this checkout via `ORIGINBA_PORTAL_DIR`
(default `~/OriginBA-3`).

    cd ~/originba_dbt && .venv/bin/python scripts/build_portal_catalog.py
