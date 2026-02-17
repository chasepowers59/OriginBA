# MCP + SQLcl Setup for Origin Utility Intelligence

This guide lets any Business Analyst reproduce the **AI-augmented workspace** so the IDE can perform **Schema Introspection** on Oracle C2M. The AI can "see" tables (e.g. `CI_BSEG`, `CI_SA`) and understand foreign key relationships without manual documentation.

## Prerequisites

- **IDE:** VS Code or Cursor (already in use).
- **Java:** Java Runtime Environment (JRE) or JDK **17** (e.g. 17.0.5 or any 17.x). SQLcl will not start without it.
- **Oracle SQLcl:** v25.2 or later.
- **Extension:** Oracle SQL Developer extension v25.2+ (install from VS Code/Cursor marketplace).

## Install Java 17 (required for SQLcl)

SQLcl needs Java 17. If you see **"This application requires a Java Runtime Environment 17.0.5"** when running `sql.exe -mcp`, install or point to Java 17.

**Option A – Adoptium (Eclipse Temurin), recommended:**
1. Go to [adoptium.net](https://adoptium.net/) and download **Temurin 17 (LTS)** for Windows (e.g. .msi installer).
2. Run the installer. Ensure **"Set JAVA_HOME variable"** and **"Add to PATH"** are enabled if offered.
3. Close and reopen your terminal, then run: `java -version` (you should see version 17.x).

**Option B – Oracle JDK 17:**  
Download from [Oracle Java SE 17](https://www.oracle.com/java/technologies/javase/jdk17-archive-downloads.html), install, and add the `bin` folder of the JRE/JDK to your PATH (or set `JAVA_HOME` to the installation root).

After installing, run `sql.exe -mcp` again; the message should disappear and the MCP server should start.

## Install Oracle SQLcl

1. Download Oracle SQLcl from Oracle (v25.2 or later).
2. Install and ensure the `sql` executable is on your system PATH.
3. Verify from a terminal:
   ```bash
   sql -version
   ```

## Install the Oracle SQL Developer Extension

1. Open VS Code or Cursor.
2. Open the Extensions view (Ctrl+Shift+X / Cmd+Shift+X).
3. Search for **Oracle SQL Developer**.
4. Install the extension (v25.2+).

## Start the MCP Server

Run the following command to start the Model Context Protocol (MCP) server:

```bash
sql -mcp
```

If you get **"sql is not recognized"**, either add SQLcl to PATH (see [Troubleshooting](#troubleshooting)) or run the executable with its full path. For example, if SQLcl is at `C:\Users\cvpow\Downloads\sqlcl-latest\sqlcl\bin\sql.exe`:

**PowerShell or CMD:**
```bash
"C:\Users\cvpow\Downloads\sqlcl-latest\sqlcl\bin\sql.exe" -mcp
```

Keep this process running (or run it as a service) so your IDE can connect to it.

## Point the IDE to SQLcl (MCP Settings)

### Cursor

1. Open Cursor Settings (or create/edit MCP configuration).
2. Point the MCP settings to your SQLcl path. Example configuration in `mcp.json` (see repo root or `.cursor/mcp.json`):

```json
{
  "mcpServers": {
    "oracle-sqlcl": {
      "command": "sql",
      "args": ["-mcp"]
    }
  }
}
```

If SQLcl is not on PATH, use the full path to the executable (use forward slashes in JSON). Example for a typical install under Downloads:

```json
{
  "mcpServers": {
    "oracle-sqlcl": {
      "command": "C:/Users/cvpow/Downloads/sqlcl-latest/sqlcl/bin/sql.exe",
      "args": ["-mcp"]
    }
  }
}
```

See [mcp.json.example](../mcp.json.example) in the repo root for a copy-paste config with this path.

**Run MCP every time you use Cursor:**  
This project includes [.cursor/mcp.json](.cursor/mcp.json) so Cursor starts the SQLcl MCP server automatically when you open the OriginBA workspace. You do **not** need to run `sql.exe -mcp` in a terminal each time. Requirements:

- **JAVA_HOME** is set permanently to your Java 17 install (e.g. `C:\Program Files\Eclipse Adoptium\jdk-17.0.18.8-hotspot`). Cursor will pass it to the SQLcl process when it starts.
- The `command` path in `.cursor/mcp.json` points to your `sql.exe`. If you move SQLcl, update that path.

After opening the project, give Cursor a moment to start the MCP server; then schema discovery in chat will use it. If the server does not start automatically, your Cursor version may use global MCP settings: open **Settings > Cursor Settings > MCP** and add the same server (command and args) there.

### VS Code (with Cline or Copilot)

Configure your MCP client (Cline, Copilot, etc.) to use the same `command` and `args` so it launches `sql -mcp` for database awareness.

## Verify Schema Introspection

Once connected, the AI assistant should be able to:

- List C2M tables and columns.
- Understand foreign key relationships between objects (e.g. `CI_BSEG`, `CI_SA`).
- Suggest or validate SQL that respects your schema.

You can ask the AI to "describe CI_BSEG" or "show relationships for CI_SA" to confirm.

## Discovery Verification (Exact Prompts)

Use these prompts in your IDE chat (with MCP connected) to confirm schema discovery is working. If the AI returns real column names and relationships from your C2M environment, discovery is set up correctly.

| Prompt | What to expect |
|--------|----------------|
| **List columns of CI_BSEG.** | Column names and types for the billing segment table. |
| **Describe the CI_BSEG table.** | Same as above; may include constraints or comments. |
| **Show foreign key relationships for CI_SA.** | Child and parent tables/columns involving CI_SA. |
| **What tables reference CI_SA?** | Tables that have FKs pointing to CI_SA. |

If the AI cannot answer using your actual schema (e.g. it guesses or says it has no access), troubleshoot: ensure `sql -mcp` is running, the IDE MCP config points to SQLcl, and SQLcl can connect to Oracle C2M (wallet, tnsnames, or connection string).

## Troubleshooting

- **`sql` not found / not recognized:** Add SQLcl's `bin` directory to your PATH so any terminal can run `sql`. On Windows:
  1. Press Win + S, type **environment variables**, open **Edit the system environment variables**.
  2. Click **Environment Variables**.
  3. Under **User variables** (or **System variables**), select **Path** and click **Edit**.
  4. Click **New** and add: `C:\Users\cvpow\Downloads\sqlcl-latest\sqlcl\bin`
  5. OK out and **close and reopen** your terminal (or Cursor) so the new PATH is picked up.
  6. Verify with: `sql -version`

  Until PATH is set, you can still start the MCP server by running the full path in a terminal: `"C:\Users\cvpow\Downloads\sqlcl-latest\sqlcl\bin\sql.exe" -mcp`. For Cursor's MCP, use the same full path in the MCP config (see above) so the IDE can launch SQLcl without relying on PATH.
- **"This application requires a Java Runtime Environment 17.0.5":** SQLcl needs Java 17. Install JRE/JDK 17 (see [Install Java 17](#install-java-17-required-for-sqlcl) above), then run `sql.exe -mcp` again.
- **MCP connection refused:** Ensure `sql -mcp` is running and the IDE MCP config points to the same SQLcl installation.
- **No schema visible:** Confirm your database connection (e.g. wallet, tnsnames, or connection string) is configured for SQLcl so it can reach Oracle C2M.

---

## Database connection (when you need schema discovery)

The MCP server can start without a database, but for the AI to **see** your C2M schema (e.g. list CI_BSEG columns, CI_SA relationships), SQLcl must be able to connect to your Oracle C2M instance.

**Do you need it now?**

| What you're doing | Need DB connection? |
|-------------------|---------------------|
| Running the Python pipeline (CSV or `--mock`) | No. Pipeline works with CSV or mock data. |
| Using AI in Cursor to write/validate C2M SQL, or to "list columns of CI_BSEG" | Yes. SQLcl needs a connection to introspect the database. |
| Building the Jaspersoft template with sample JSON | No. Template uses the JSON file the pipeline produces. |

**When you're ready to connect SQLcl to C2M:**

1. **Get connection details** from your DBA or C2M docs: host, port, service name (or SID), and optionally wallet path.
2. **Option A – TNS (tnsnames.ora):**  
   Create or edit `tnsnames.ora` with an entry for your C2M database. Place it somewhere SQLcl can find it (e.g. `C:\Users\cvpow\Downloads\sqlcl-latest\sqlcl\network\admin\` or set `TNS_ADMIN` to that folder). Example:
   ```
   C2M_PROD = (DESCRIPTION = (ADDRESS = (PROTOCOL = TCP)(HOST = your-host)(PORT = 1521)) (CONNECT_DATA = (SERVICE_NAME = your_service)))
   ```
   Then connect with: `sql username/password@C2M_PROD`
3. **Option B – Wallet:**  
   If your org uses a wallet, set `TNS_ADMIN` to the wallet directory and use the wallet connection string in your connect command.
4. **Option C – Easy connect:**  
   `sql username/password@host:port/service_name`
5. **Test:** In a terminal (with JAVA_HOME set), run your `sql.exe` and connect. Once connected, the MCP server can use that connection for schema introspection when you use it from Cursor.

Connection is typically configured **per session** (you connect when you start SQLcl) or via a saved connection in the Oracle SQL Developer extension. For MCP, the exact flow depends on how SQLcl MCP is implemented (e.g. whether it prompts for connection or uses a default). If the AI still can't see schema after you've connected once, check the SQLcl MCP docs or your DBA for the recommended way to persist the C2M connection for the MCP server.
