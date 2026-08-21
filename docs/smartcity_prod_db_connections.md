# SmartCity Production Database Connections

Read-only access for validation and reporting parity work. Credentials live in
local `.env` only (`SMARTCITY_PROD_*` and per-client `*_PROD_ORACLE_DSN`).

## Hosts

Most legacy PROD clients still use the shared host below. CityCorp 25.4 PROD
uses the newer `v1-2` host/service.

| Field | Value |
| --- | --- |
| Shared host (legacy) | `smartcity-db-prod.originsmartops.com` |
| CityCorp 25.4 PROD host | `smartcity-db-prod-v1-2.originsmartops.com` |
| Port | `1521` |
| User | `CPOWERS` (from Bitwarden / ops send; per-client password may differ) |

## Service names

| Client | Service name |
| --- | --- |
| Newark | `pproddb_newark.prodprivatesn.originprodvcn.oraclevcn.com` |
| Fond du Lac | `pproddb_fonddulac.prodprivatesn.originprodvcn.oraclevcn.com` |
| College Station | `pproddb_collegestation.prodprivatesn.originprodvcn.oraclevcn.com` |
| Ellensburg | `pproddb_ellensburg.prodprivatesn.originprodvcn.oraclevcn.com` |
| CityCorp 25.4 PROD | `PPRODDB_CITYCORP.prodprivatesn.prodvcn.oraclevcn.com` |

## Runner aliases

```bash
python3 scripts/local/run_client_oracle_sql.py --client citycorp_prod --sql "select sysdate from dual"
python3 scripts/local/run_client_oracle_sql.py --client newark_prod --sql "select sysdate from dual"
python3 scripts/local/run_client_oracle_sql.py --client fonddulac_prod --sql "select sysdate from dual"
python3 scripts/local/run_client_oracle_sql.py --client collegestation_prod --sql "select sysdate from dual"
python3 scripts/local/run_client_oracle_sql.py --client ellensburg_prod --sql "select sysdate from dual"
```

## Safety

- Use **SELECT-only** SQL from this repo's validation scripts.
- Do not run deployment_steps refresh/procedure scripts against PROD without
  explicit change control.
- Never commit `.env` or paste passwords into tickets or JRXML.
