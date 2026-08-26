# Origin_INT_DEV_DS

Separate JDBC datasource for **INT_DEV / pdevdb** (Origin Development 25.4).

Use this when `/DataSource/Origin_DEV_DS` on the server already points at a client TEST DB (e.g. Ellensburg). Importing under the alias `Origin_INT_DEV_DS` will **not** overwrite `Origin_DEV_DS`.

| Setting | Value |
| --- | --- |
| Alias | `Origin_INT_DEV_DS` |
| Host | `10.16.0.89` |
| Port | `1521` |
| Service | `pdevdb_demo.devprivatesn.devvcn.oraclevcn.com` |
| JDBC URL | `jdbc:oracle:thin:@10.16.0.89:1521/pdevdb_demo.devprivatesn.devvcn.oraclevcn.com` |
| Connection user (export) | `JRS2C2M_DEV` |
| SQL client key (`.env`) | `int_dev` |

## Import

Zip: `deploy/jaspersoft_datasources/canonical/Origin_INT_DEV_DS_export.zip`

1. In Jaspersoft, open the **organization that already has** `/DataSource/Origin_DEV_DS` (do not import at server root).
2. Import this zip into that org.
3. Confirm `/DataSource/Origin_INT_DEV_DS` appears next to `Origin_DEV_DS`.
4. Test the connection and re-save the password if the bundled encrypted credential does not decrypt.

This zip **omits** `rootTenantId` on purpose. Exports that set `rootTenantId=Origin_DEV` and are imported from server root fail with: `Import of an organization to the root is not allowed`.

## Warehouse schemas

Point Domains/Ad Hoc schema aliases at:

- `ORIGINBA_LANDING`
- `ORIGINBA_STAGING`
- `ORIGINBA_CORE`
- `ORIGINBA_REPORTING`

(once created; grant `JRS2C2M_DEV` SELECT as needed)

## Do not confuse with

- `Origin_DEV_DS` — often used as the org’s primary DEV/TEST alias (may be Ellensburg on server)
- `Training_DB` — INT_TRAIN / ptrndb
