# 01 — Oracle & Jaspersoft connections

No passwords. Values are host/service/user identity only. Confirmed from Chase Mac `.env` key presence + DSN parsing on 2026-08-11.

## Two identities (do not confuse)

| Identity | Used for | Notes |
|----------|----------|-------|
| `CPOWERS` | Live SQL via Cursor runner / MCP | Personal account; read-only by contract |
| `JRS2C2M` | Jaspersoft Server JDBC datasources | In client DS XML under `deploy/jaspersoft_datasources/clients/` |

## How to pick a client

```bash
python3 scripts/local/run_client_oracle_sql.py --client <alias> --sql "SELECT USER FROM dual"
```

| Alias (`--client`) | Env prefix | Typical use |
|--------------------|------------|-------------|
| `int_dev` | `INT_DEV` | Origin DEV baseline (prefer for lookups) |
| `int_train` | `INT_TRAIN` | Internal train |
| `demo` | `DEMO` | SmartCity demo |
| `ellensburg` | `ELLENSBURG` | Ellensburg TEST |
| `newark` | `NEWARK` | Newark TEST |
| `citycorp` | `CITYCORP` | CityCorp TEST |
| `fonddulac` | `FONDDULAC` | Fond du Lac TEST |
| `collegestation` | `COLLEGESTATION` | College Station TEST |
| `odessa` | `ODESSA` | Odessa TEST |
| `odessa_dev` | `ODESSA_DEV` | Odessa DEV |
| `*_prod` | `*_PROD` | Production (VPN + prod creds; MCP off by default) |

## Live connection map (TEST / internal)

| Alias | User | Host | Port | Service |
|-------|------|------|------|---------|
| `int_dev` | CPOWERS | 10.16.0.89 | 1521 | pdevdb_demo.devprivatesn.devvcn.oraclevcn.com |
| `int_train` | CPOWERS | smartcity-db-demo.originsmartops.com | 1521 | ptrndb_demo.demoprivatesn2.origindemovcn.oraclevcn.com |
| `demo` | CPOWERS | smartcity-db-demo.originsmartops.com | 1521 | pdemodb_demo.demoprivatesn2.origindemovcn.oraclevcn.com |
| `ellensburg` | CPOWERS | smartcity-db-test-v1-2.originsmartops.com | 1521 | PTESTDB_ELLENSBURG.testprivatesn.testvcn.oraclevcn.com |
| `newark` | CPOWERS | smartcity-db-test-v1-2.originsmartops.com | 1521 | PTESTDB_NEWARK.testprivatesn.testvcn.oraclevcn.com |
| `fonddulac` | CPOWERS | smartcity-db-test-v1-2.originsmartops.com | 1521 | PTESTDB_FONDDULAC.testprivatesn.testvcn.oraclevcn.com |
| `collegestation` | CPOWERS | smartcity-db-test-v1-2.originsmartops.com | 1521 | PTESTDB_COLLEGESTATION.testprivatesn.testvcn.oraclevcn.com |
| `citycorp` | CPOWERS | 10.13.4.91 | 1521 | ptestdb_citycorp.testprivatesn.testvcn.oraclevcn.com |
| `odessa` | CPOWERS | smartcity-db-test2.originsmartops.com | 1521 | ptestdb_odessa.testprivatesn.testvcn.oraclevcn.com |
| `odessa_dev` | CPOWERS | 10.16.0.225 | 1521 | pdevdb_odessa.devprivatesn.devvcn.oraclevcn.com |

## Production aliases (exist; use with care)

| Alias | Host | Service (prefix) |
|-------|------|------------------|
| `newark_prod` | smartcity-db-prod.originsmartops.com | pproddb_newark... |
| `fonddulac_prod` | smartcity-db-prod.originsmartops.com | pproddb_fonddulac... |
| `collegestation_prod` | smartcity-db-prod.originsmartops.com | pproddb_collegestation... |
| `ellensburg_prod` | smartcity-db-prod.originsmartops.com | pproddb_ellensburg... |
| `citycorp_prod` | smartcity-db-prod-v1-2.originsmartops.com | PPRODDB_CITYCORP... |

## `.env` key schema (names only)

Runner consumes **full DSN** keys, not assembled host/port/service at runtime.

### Per client
- `{PREFIX}_DB_USER`
- `{PREFIX}_DB_PASSWORD`
- `{PREFIX}_ORACLE_DSN`  **(primary)**  format `host:1521/service`
- `{PREFIX}_DB_CONNECT_STRING` (fallback if DSN missing)
- Optional docs-only: `{PREFIX}_DB_HOST`, `{PREFIX}_DB_PORT`, `{PREFIX}_DB_SERVICE_NAME`

### Fallbacks (`client_connection`)
1. User: `{PREFIX}_DB_USER` → `DEMO_DB_USER` → `DB_USER` → `ORACLE_USER`
2. Password: `{PREFIX}_DB_PASSWORD` → `DEMO_DB_PASSWORD` → `DB_PASSWORD` → `ORACLE_PASSWORD`
3. Prod: also tries `SMARTCITY_PROD_DB_USER` / `SMARTCITY_PROD_DB_PASSWORD`

### Thick mode / timeouts
- `ORACLE_CLIENT_LIB_DIR` — Instant Client directory (this Mac: `/Users/chase/Downloads/instantclient_23_26`)
- `DB_THICK_MODE=true`
- `DB_CALL_TIMEOUT_MS` — runner default often `900000` (15 min)
- `DB_FETCH_ARRAY_SIZE`

### Example: `int_dev` on this Mac
- Has `INT_DEV_ORACLE_DSN` / connect string
- Often **no** `INT_DEV_DB_USER` / `INT_DEV_DB_PASSWORD` → falls back to `DEMO_*` / `ORACLE_*` → resolves as `CPOWERS`

## Jaspersoft datasource aliases (server overlays)

Mapping file: `deploy/jaspersoft_client_promotion/client_org_mapping.csv`

| Jaspersoft org / client | Datasource alias | Canonical folder |
|-------------------------|------------------|------------------|
| Ellensburg | Ellensburg_DS | `deploy/jaspersoft_datasources/clients/Ellensburg_DS/` |
| Newark1 | Newark1_DS | `.../Newark1_DS/` |
| CityCorp | CityCorp_DS | `.../CityCorp_DS/` |
| CityCorp PROD | CityCorp_PROD_DS | `.../CityCorp_PROD_DS/` |
| College_Station | CollegeStation_DS | `.../CollegeStation_DS/` |
| Fond_Du_Lac | FondDuLac_DS | `.../FondDuLac_DS/` |
| Odessa | Origin_DataVergence_DS | `.../Origin_DataVergence_DS/` |

Internal aliases used in reports/docs: `ORIGIN_DEV_DS`, `C2M_QA_DS`, `C2M_PROD_DS` (contract names; client packs use client-specific `*_DS`).

## Network

- Corporate VPN required for private DNS (`*.originsmartops.com`) and private IPs (`10.16.x`, `10.13.x`).
- Without VPN: hostname resolve failures (`ORA-12262`) or TCP timeout (`ORA-12170`).
- Listener port: **1521**.
- Exact VPN profile name is not stored in repo.
