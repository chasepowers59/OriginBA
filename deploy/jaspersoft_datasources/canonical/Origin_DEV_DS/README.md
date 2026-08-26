# Origin_DEV_DS (Origin_DEV tenant)

Canonical JDBC datasource for **INT_DEV / pdevdb** — Origin Development **25.4**.

| Setting | Value |
| --- | --- |
| Alias | `Origin_DEV_DS` |
| Tenant | `Origin_DEV` |
| Host | `10.16.0.89` |
| Port | `1521` |
| Service | `pdevdb_demo.devprivatesn.devvcn.oraclevcn.com` |
| JDBC URL | `jdbc:oracle:thin:@10.16.0.89:1521/pdevdb_demo.devprivatesn.devvcn.oraclevcn.com` |
| Connection user (export) | `JRS2C2M_DEV` |
| SQL client key (`.env`) | `int_dev` |

This is the same database used for dbt warehouse schema testing (landing / staging / core / reporting). One datasource reaches the whole DB; Domains and Ad Hoc should set **schema alias** to `CISADM` for source reads or to `ORIGINBA_LANDING` / `ORIGINBA_STAGING` / `ORIGINBA_CORE` / `ORIGINBA_REPORTING` for warehouse layers (once those schemas exist and `JRS2C2M_DEV` has SELECT grants).

**If server `Origin_DEV_DS` already points at Ellensburg (or another client TEST):** do not re-import this alias — use **`Origin_INT_DEV_DS`** instead (`canonical/Origin_INT_DEV_DS_export.zip`) so you keep both connections.

## Import

Prefer the zip:

`deploy/jaspersoft_datasources/canonical/Origin_DEV_DS_export.zip`

Import into the **Origin_DEV** organization as `/DataSource/Origin_DEV_DS`. After import, test the connection in Jaspersoft and re-save the password if the bundled encrypted credential does not decrypt on your server.

Expanded source files (same content): `resources/DataSource/Origin_DEV_DS.xml`.

## Do not confuse with

- `Training_DB` — INT_TRAIN / `ptrndb` (demo VCN training snapshots)
- `Origin_STAGE_DS` — Stage / pstgdb
- Client aliases (`Ellensburg_DS`, etc.) — client TEST/PROD only
