# Origin_STAGE_DS — pstgdb revert archive (2026-06-08)

Archive of `Origin_STAGE_DS` on **pstgdb** (`10.16.0.89`). Kept when adding separate
`Training_DB` → ptrndb for snapshot-backed Standard Offering (does not replace this datasource).

## Previous connection (pstgdb — internal Stage host)

| Field | Value |
| --- | --- |
| Alias | `Origin_STAGE_DS` |
| Host | `10.16.0.89` |
| Service | `pstgdb_demo.devprivatesn.devvcn.oraclevcn.com` |
| JDBC URL | `jdbc:oracle:thin:@10.16.0.89:1521/pstgdb_demo.devprivatesn.devvcn.oraclevcn.com` |
| User | `JRS2C2M_STGE` |

Full datasource XML: `resources/DataSource/Origin_STAGE_DS.xml`  
Export ZIP backup: `Origin_STAGE_DS_export.zip`

## Revert to pstgdb

1. Restore canonical datasource XML:

```bash
cp deploy/jaspersoft_datasources/archive/Origin_STAGE_DS_pstgdb_20260608/resources/DataSource/Origin_STAGE_DS.xml \
   deploy/jaspersoft_datasources/canonical/Origin_STAGE_DS/resources/DataSource/Origin_STAGE_DS.xml
```

2. Restore `connectionUrl` in `deploy/jaspersoft_environment_promotion/environment_profiles.json`
   under `origin_stage.datasource` to the pstgdb JDBC URL above.

3. Rebuild the Stage Standard Offering import ZIP:

```bash
python3 scripts/jaspersoft/run_environment_import_pipeline.py \
  --environment origin_stage \
  --source-zip "/path/to/standard offering.zip" \
  --outdir deploy/jaspersoft_environment_promotion/prepared_imports \
  --datasource-export-dir deploy/jaspersoft_datasources/canonical \
  --skip-archive
```

4. Re-import inside the `Origin_STAGE` tenant, or update the datasource in the
   Jaspersoft UI and test the connection.

## New connection (ptrndb — Int Train / snapshots)

| Field | Value |
| --- | --- |
| Host | `smartcity-db-demo.originsmartops.com` |
| Service | `ptrndb_demo.demoprivatesn2.origindemovcn.oraclevcn.com` |
| JDBC URL | `jdbc:oracle:thin:@smartcity-db-demo.originsmartops.com:1521/ptrndb_demo.demoprivatesn2.origindemovcn.oraclevcn.com` |
| User | `JRS2C2M_STGE` (unchanged; test in JRS after deploy) |

Client key for SQL rollout / snapshot validation: `int_train` in `.env`.
