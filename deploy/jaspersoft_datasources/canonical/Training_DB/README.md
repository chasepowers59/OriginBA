# Training_DB (Origin_STAGE tenant)

Secondary JDBC datasource for **Int Train / ptrndb** (internal snapshot tables).

- Does **not** replace `Origin_STAGE_DS` (pstgdb on `10.16.0.89`).
- Standard Offering imports for Stage rewrite all package datasource references to
  `/DataSource/Training_DB`.

After import, test the connection in Jaspersoft and re-save the password if the
bundled `JRS2C2M` credential does not decrypt on the internal Stage server.

SQL rollout client key: `int_train` in `.env`.
