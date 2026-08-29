# Origin_DEV_DS → Ellensburg 25.4 TEST

Import bundle that **replaces** `/DataSource/Origin_DEV_DS` with Ellensburg TEST **25.4** (`PTESTDB_ELLENSBURG` on `smartcity-db-test-v1-2`).

| Setting | Value |
| --- | --- |
| Alias | `Origin_DEV_DS` |
| Host | `10.13.4.91` (JRS-reachable scan IP; same DB as `smartcity-db-test-v1-2`) |
| Port | `1521` |
| Service | `ptestdb_ellensburg.testprivatesn.testvcn.oraclevcn.com` |
| JDBC URL | `jdbc:oracle:thin:@10.13.4.91:1521/ptestdb_ellensburg.testprivatesn.testvcn.oraclevcn.com` |
| Connection user | `JRS2C2M` |
| SQL client key (`.env`) | `ellensburg` |

## Import

Zip: `deploy/jaspersoft_datasources/canonical/Origin_DEV_DS_Ellensburg_25_4_export.zip`

1. In Jaspersoft, open the **Origin_DEV** organization (not server root).
2. Repository → Import → select this zip → **Update** existing resources when prompted.
3. Confirm `/DataSource/Origin_DEV_DS` shows host `10.13.4.91` and service `ptestdb_ellensburg...`.
4. Test the connection. If it fails, re-enter the `JRS2C2M` password and save (encrypted export passwords often fail after import).

**Quick sanity check:** In the **Ellensburg** org, open `/DataSource/Ellensburg_DS` and test that connection. If Ellensburg_DS works, copy its JDBC URL + password into `Origin_DEV_DS` manually.

This zip **omits** `rootTenantId` on purpose (same pattern as `Origin_INT_DEV_DS_export.zip`) so import from the org context does not fail with `Import of an organization to the root is not allowed`.

## Before you override

If you still need **INT_DEV / pdevdb**, import `Origin_INT_DEV_DS_export.zip` first so pdevdb remains available under a separate alias.

## Do not confuse with

- `canonical/Origin_DEV_DS_export.zip` — INT_DEV / pdevdb (not Ellensburg)
- `clients/Ellensburg_DS/` — same DB under the Ellensburg tenant alias
