# Jaspersoft BI Reports: JSONQL (Story) vs JDBC (Evidence)

This guide describes how to use the pipeline output and C2M data in Jaspersoft for BI reports (Arrearage, Payment Integrity, Bankruptcy Monitor).

## Split: Story vs Evidence

| Source | Adapter | Content |
|--------|---------|---------|
| **Pipeline output** (`output/narrative.json`) | **JSONQL** | The **story**: AI-generated narrative and headline metrics (total_debt, debt_30_days, duplicate_payment_account_count, bankruptcy_alert_count, etc.). Use for Summary Band and KPI highlights. |
| **C2M database** (Oracle) | **JDBC** | The **evidence**: Row-level tables (Detailed Running Arrear Balance, Duplicate Payment rows, Bankruptcy payment rows, Master Deposit Reconciliation). Use for Detail bands, tables, and charts. |

The pipeline does **not** export row-level evidence. Evidence tables are produced by running the governed SQL **inside Jaspersoft** via a JDBC data adapter to C2M.

---

## JSONQL Adapter (Story and Metrics)

1. Create a **JSONQL Data Adapter** (or file data source) that points to the pipeline output: `output/narrative.json` (or the path in `NARRATIVE_JSON_PATH`).
2. Map fields to the report:
   - **narrative** → Text field in the Summary Band (set **Text Adjust = StretchHeight**).
   - **total_debt**, **debt_30_days**, **debt_60_days**, **debt_over_60** → Variables or text fields for arrears KPIs.
   - **large_bill_count** → KPI display.
   - **duplicate_payment_account_count**, **duplicate_payment_example_amt** → Payment integrity highlights.
   - **bankruptcy_alert_count**, **bankruptcy_pym_amt** → Bankruptcy risk highlights.

Field names must match the pipeline output schema in [pipeline.md](pipeline.md).

---

## JDBC Adapter (Evidence Tables)

Use a **JDBC data adapter** connected to Oracle C2M (same credentials as in `.env`). Run the governed SQL **in the report** (e.g. as the report query or a subdataset query). Do **not** generate SQL at runtime; use the stored queries below.

### Queries for Evidence (copy into Jaspersoft)

- **Detailed Running Arrear Balance** – Row-level aging and running arrear balance per SA. Use for an “Evidence” table or chart. SQL: [sql/arrears_detailed.sql](../sql/arrears_detailed.sql). Pipeline runs only Strategic Arrears Summary; this query is for JDBC only.
- **Duplicate Payment Detection** – Row-level list of accounts with same payment amount today and yesterday. The pipeline runs this and aggregates the count; for an evidence table, run the same query via JDBC. SQL: [sql/duplicate_payment.sql](../sql/duplicate_payment.sql).
- **Bankruptcy Monitor** – Row-level list of bankruptcy-flagged accounts and their payment activity. Same as above: pipeline aggregates; for evidence table, run the same query via JDBC. SQL: [sql/bankruptcy_monitor.sql](../sql/bankruptcy_monitor.sql).
- **Master Deposit Reconciliation** – Payment events and deposit labels for bank reconciliation. Not run by the pipeline. SQL: [sql/deposit_reconciliation.sql](../sql/deposit_reconciliation.sql).

Reports that need **evidence tables** should use JDBC with these governed queries (or the equivalent `.sql` files in `sql/`). The narrative and headline numbers always come from the pipeline JSON via JSONQL.

---

## Jaspersoft report with NLQ (parameter-driven narrative)

Connect the **Story** (AI narrative) to the **Evidence** (JDBC tables) in the report layout so clients can run a search and see the narrative plus verifying detail.

### 1. Create a report parameter

In Jaspersoft Studio, create a report parameter named **P_SEARCH_QUERY** (String). This is the natural language question or account lookup (e.g. "What is the status of Account 2927873805?" or "123 Main St"). The user types it into the report’s input control; you use it to call the NLQ API.

### 2. Configure the Data Adapter for the Story

Set up a **JSONQL Data Adapter** (or REST/HTTP adapter that returns JSON) that calls your NLQ API:

- **URL (GET):** `http://localhost:8000/nlq?query=$P!{P_SEARCH_QUERY}`  
  (Use the appropriate syntax for your adapter so the parameter value is URL-encoded and substituted into the `query` parameter.)

If you use **NLQ_API_KEY** (recommended in production), your adapter must send the header **X-API-Key** with each request. Not all JSONQL adapters support custom headers; if yours does not, use a REST client data adapter that allows headers, or run the API locally without `NLQ_API_KEY` for development only.

Ensure the API is running (e.g. `uvicorn api.nlq_server:app --host 0.0.0.0 --port 8000` from the repo root).

### 3. Map the fields

Map the **narrative** field from the JSON response to a **text element** in the **Summary Band**. Set **Text Adjust = StretchHeight** so the narrative wraps. Optionally map **acct_id**, **metrics.total_debt**, etc., to variables or text fields for KPIs next to the narrative.

### 4. Add evidence tables below the narrative

Use your existing **JDBC** connection to C2M to place a **detailed aging table** (evidence) below the narrative so the client can verify the AI’s claims. Use the governed SQL from [sql/arrears_detailed.sql](../sql/arrears_detailed.sql) (Working file.sql–style detailed running arrear balance). Add a **Detail band** with a table component whose data source is the JDBC adapter and query from `arrears_detailed.sql`. Optionally filter the evidence table by the account resolved by NLQ (e.g. pass **acct_id** from the NLQ response into the JDBC query or a subdataset filter).

Result: the user enters a search (account, address, or name) in **P_SEARCH_QUERY**, the Summary Band shows the AI narrative and key metrics, and the table below shows the row-level evidence from C2M.
