# Database Connections (Oracle C2M)

Use the same dev username and password across the pipeline, SQLcl (MCP), and Jaspersoft Studio. This doc explains how each tool connects.

## Credentials in .env

Put your Oracle dev credentials in `.env` (never commit `.env`; it is in `.gitignore`):

```env
ORACLE_USER=your_dev_username
ORACLE_PASSWORD=your_dev_password
ORACLE_DSN=host:port/service_name
```

- **ORACLE_DSN** = same connection info you use in SQL Developer. Examples:
  - Easy connect: `myhost.example.com:1521/C2MDEV`
  - If you use a TNS name (e.g. `C2M_PROD`), you can set **ORACLE_DSN** to that name only if `TNS_ADMIN` is set and `tnsnames.ora` contains that entry; otherwise use the long form `host:port/service_name`.

If your Oracle server **requires Native Network Encryption or Data Integrity**, you must use python-oracledb in **thick mode**. Set **ORACLE_CLIENT_LIB_DIR** in `.env` to the directory containing the Oracle Instant Client libraries (e.g. `C:\oracle\instantclient_19_21` or `/opt/oracle/instantclient_19_21`). See [Thick mode (network encryption)](#thick-mode-network-encryption) below.

The **Python pipeline** reads these variables and connects to Oracle when you run `python -m pipeline.main` (no `--mock`, no `--csv`). See [Pipeline](#python-pipeline) below.

---

## Python Pipeline

With `ORACLE_USER`, `ORACLE_PASSWORD`, and `ORACLE_DSN` set in `.env`:

1. Activate your venv and install deps (includes `oracledb`):
   ```bash
   pip install -r pipeline/requirements.txt
   ```
2. Run the pipeline **without** `--mock` and **without** `--csv`:
   ```bash
   python -m pipeline.main
   ```
   The pipeline will connect to Oracle, run a governed query against `CI_BSEG` (FREEZE_SW = 'Y', 90-day window), and use the last two billing rows for the narrative.

If any of the three Oracle variables is missing, the pipeline falls back to CSV (or fails if the CSV is missing). Use `--mock` to test without DB or CSV.

---

## Thick mode (network encryption)

If you see **DPY-3001: Native Network Encryption and Data Integrity is only supported in python-oracledb thick mode** (or **DPY-6005: cannot connect to database** with that cause), the server is enforcing encryption and the default thin mode cannot be used.

1. **Install Oracle Instant Client** (same major version as your server, e.g. 19.x or 21.x):
   - **Windows 64-bit:** [Instant Client for Windows x64](https://www.oracle.com/database/technologies/instant-client/winx64-64-downloads.html) (download Basic or Basic Light ZIP). **Linux:** [Instant Client downloads](https://www.oracle.com/database/technologies/instant-client/downloads.html) — choose “Instant Client for Microsoft Windows” or Linux x86_64, and the “Basic” or “Basic Light” package.
   - Unzip to a directory such as `C:\oracle\instantclient_19_21` or `/opt/oracle/instantclient_19_21`.
2. In `.env`, set **ORACLE_CLIENT_LIB_DIR** to that directory:
   ```env
   ORACLE_CLIENT_LIB_DIR=C:\oracle\instantclient_19_21
   ```
   (Use the path where you unzipped Instant Client; use forward slashes on Windows if needed.)
3. Run the pipeline again. The first Oracle connection in the process will initialize thick mode; subsequent connections in the same run use it automatically.

If **ORACLE_CLIENT_LIB_DIR** is not set and the server does not require encryption, the pipeline uses thin mode (no Oracle Client install needed).

**NLQ premise and customer-name resolution:** The Natural Language Query (NLQ) feature can resolve an address/premise or a customer name to account ID(s) using governed SQL only. The queries are defined in `pipeline/fetch_usage.py` and documented in `sql/premise_to_acct_mapping.sql` and `sql/customer_name_to_acct.sql`. Until you replace those placeholders with your real C2M mapping logic (e.g. CI_ACCT, premise/address tables, or customer name views), place/name lookups return no accounts and the AI responds that it does not have access. When your mapping tables are ready, update the governed SQL constants in `fetch_usage.py` (or the referenced `.sql` files) with the correct tables and bind parameters.

---

## SQLcl (MCP / Schema Discovery)

SQLcl does **not** read `.env`. To use the same credentials for schema discovery (e.g. “list columns of CI_BSEG” in Cursor):

1. Start SQLcl (e.g. run `sql.exe -mcp` or let Cursor start it via MCP).
2. Connect with the same user, password, and destination:
   - If your **ORACLE_DSN** is `myhost:1521/C2MDEV`, in SQLcl you’d run:
     ```text
     connect your_dev_username/your_dev_password@myhost:1521/C2MDEV
     ```
   - Or, if you use a TNS name (e.g. `C2M_PROD`): `connect user/pass@C2M_PROD`.

After that, the MCP server can use this session for schema introspection. Exact behavior (e.g. whether you must connect in a separate SQLcl window or the MCP server prompts) depends on your SQLcl MCP setup; the important part is that the **same username, password, and DSN** you put in `.env` are used when connecting in SQLcl.

---

## Jaspersoft Studio

In Jaspersoft Studio you create a **JDBC Data Source** (or similar) and enter the same connection details.

1. In Studio: **Window → Data Adapters** (or **Report → Data Adapter** depending on version).
2. Create a new **Database JDBC** (or **Oracle**) data adapter.
3. Use the same values as in `.env`:
   - **Driver:** Oracle Thin (e.g. `oracle.jdbc.OracleDriver`).
   - **URL:** `jdbc:oracle:thin:@//host:port/service_name`  
     If your **ORACLE_DSN** is `myhost:1521/C2MDEV`, the URL is:  
     `jdbc:oracle:thin:@//myhost:1521/C2MDEV`  
     (Some setups use `@host:port:sid`; use the format your JDBC driver expects.)
   - **Username:** same as `ORACLE_USER`.
   - **Password:** same as `ORACLE_PASSWORD`.

For the **Personalized Monthly Statement** report, you can use this adapter for live usage data in the report, or keep using the **JSONQL** adapter that reads the narrative JSON produced by the Python pipeline. This JDBC adapter is for reports that query C2M directly; the narrative itself still comes from the pipeline JSON.

---

## Summary

| Tool              | Where credentials live        | How to connect |
|-------------------|-------------------------------|----------------|
| **Python pipeline** | `.env` (ORACLE_USER, ORACLE_PASSWORD, ORACLE_DSN) | Set in `.env`; run `python -m pipeline.main`. |
| **SQLcl (MCP)**   | Not in .env                   | In SQLcl: `connect user/pass@host:port/service_name` (same as ORACLE_DSN). |
| **Jaspersoft Studio** | Entered in the adapter dialog | New JDBC adapter: URL `jdbc:oracle:thin:@//host:port/service_name`, same user/password. |

Use the **same** username, password, host, port, and service name (or TNS name) in all three.

---

## Oracle permissions (read-only)

Before any client-facing rollout, verify that the database user used by the Python pipeline has **read-only** access to the CISADM schema. The pipeline and NLQ resolution queries use only **SELECT** against tables such as:

- **CI_FT**, **CI_SA**, **CI_ACCT**, **CI_SA_TYPE** (BI and arrears)
- **CI_PREM** (premise/address for NLQ)
- **CI_PER_NAME**, **CI_ACCT** (customer name for NLQ)
- **CI_ACCT_ALERT** (bankruptcy monitor)

Ensure the user has no INSERT, UPDATE, DELETE, or DDL privileges on these tables (or use a dedicated read-only role). This limits risk if credentials are ever exposed and keeps the pipeline aligned with governance. See [semantic-layer.md](semantic-layer.md).
