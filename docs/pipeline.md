# Python-to-Jasper AI Pipeline

This pipeline fetches data (from Oracle C2M or CSV), calls **OpenAI** or **Gemini** to generate a narrative, and writes a JSON file for the Jaspersoft JSONQL Data Adapter. Set `OPENAI_API_KEY` (and optionally `OPENAI_MODEL`) in `.env` to use OpenAI; otherwise set `GEMINI_API_KEY` to use Gemini.

**Modes:**
- **Oracle connected:** Runs three governed BI queries (Arrears, Payment Integrity, Bankruptcy Monitor), aggregates key metrics, and generates a **Senior BI Analyst** narrative. Output includes `narrative` plus BI metrics (e.g. `total_debt`, `debt_30_days`, `duplicate_payment_account_count`, `bankruptcy_alert_count`).
- **CSV or --mock:** Uses usage/billing data and generates a short bill narrative. Output includes `narrative` plus usage KPIs (`current_amount`, `prior_amount`, etc.).

## Isolate Dependencies: Use a Virtual Environment

To avoid conflicts with other tools (e.g. gemini-cli) and keep the Origin build stable, use a dedicated venv for this project:

```bash
cd OriginBA
python -m venv venv
venv\Scripts\activate   # Windows
# source venv/bin/activate   # macOS/Linux
pip install -r pipeline/requirements.txt
```

Then run the pipeline from the repo root with the venv active: `python -m pipeline.main --mock`.

**Read-only:** The pipeline only runs **SELECT** queries against C2M. No INSERT, UPDATE, DELETE, or DDL. See [semantic-layer.md](semantic-layer.md).

## How to Run

### Prerequisites

- Python 3.10+
- **Recommended:** Create and activate the project venv (see above), then install dependencies:

  ```bash
  pip install -r pipeline/requirements.txt
  ```

- Copy `.env.example` to `.env` and set `GEMINI_API_KEY`.

### One Command

From the repo root:

```bash
python -m pipeline.main
```

Or from the `pipeline/` directory:

```bash
python main.py
```

- **With Oracle C2M:** If you set `ORACLE_USER`, `ORACLE_PASSWORD`, and `ORACLE_DSN` in `.env`, the pipeline runs the **BI pipeline**: three governed queries (Strategic Arrears, Duplicate Payment Detection, Bankruptcy Monitor), aggregates metrics, and generates a Senior BI Analyst narrative. No `--csv` needed.
- **With CSV:** Otherwise it expects a usage CSV at `data/usage.csv` (or `USAGE_CSV_PATH`). If you have neither, run with mock data:

```bash
python -m pipeline.main --mock
```

### Options

| Option | Description |
|--------|-------------|
| `--mock` | Use hardcoded usage summary (no CSV). Use to test Gemini and JSON output. |
| `--csv PATH` | Path to usage CSV (overrides `USAGE_CSV_PATH`). |
| `--output PATH` | Path for output JSON (overrides `NARRATIVE_JSON_PATH`). |

### Environment Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `OPENAI_API_KEY` | One of OpenAI or Gemini required | — | OpenAI API key; when set, narrative uses OpenAI. |
| `OPENAI_MODEL` | No | `gpt-4o-mini` | OpenAI model name. |
| `GEMINI_API_KEY` | One of OpenAI or Gemini required | — | Gemini API key; used when OPENAI_API_KEY is not set. |
| `GEMINI_MODEL` | No | `gemini-2.0-flash` | Gemini model name. |
| `USAGE_CSV_PATH` | No | `data/usage.csv` | Path to usage CSV. |
| `NARRATIVE_JSON_PATH` | No | `output/narrative.json` | Path to write narrative JSON. |
| `ORACLE_USER` / `ORACLE_PASSWORD` / `ORACLE_DSN` | No | — | Oracle C2M connection (same as SQL Developer). If set, pipeline fetches usage from DB instead of CSV. See [database-connections.md](database-connections.md). |
| `RISK_DATA_ENABLED` | No | (off) | Set to `1` or `true` to run Risk Data queries (Revenue Leakage, Liquidity Risk, Stale Pending SA). Merges risk metrics into BI summary and narrative. See [semantic-layer.md](semantic-layer.md#audit-mode-risk-data). |

### Audit vs Reporting Mode

- **Reporting Mode (default):** BI pipeline uses **Clean Data** only—frozen financial facts (`FREEZE_SW = 'Y'`), active SAs (`SA_STATUS_FLG = '20'`). Suitable for financial statements and standard dashboards.
- **Audit Mode:** Set `RISK_DATA_ENABLED=1` to include **Risk Data**—canceled SAs with unresolved debt, pending/unfrozen payments (>48h), stale pending service agreements. The narrative and Business Snapshot will include "Unresolved Debt on Canceled Service," "Suspense Account Alert," and "Service delay detected" when applicable. Use for operational monitoring and Senior Data Auditor workflows.

## Input: Oracle or CSV

When not using `--mock`, the pipeline uses Oracle C2M (if `ORACLE_*` are set in `.env`) or a CSV. For using the **same credentials in SQLcl and Jaspersoft Studio**, see [database-connections.md](database-connections.md).

**If using CSV,** expected columns (names can vary; see `fetch_usage.py`):

- **Period / date:** `period_end` or `bill_dt` (for sorting current vs prior month).
- **Amount:** `amount` or `bill_amt` (currency).
- **Usage:** `usage_kwh` or `total_usage` (optional).
- **Weather:** `heatwave_days` (optional, for narrative context).

Export from C2M using governed SQL (see `docs/semantic-layer.md` and `sql/governance_snippets.sql`), then point `USAGE_CSV_PATH` to that file.

## Output: JSON Schema

The pipeline writes a single JSON object used by the Jasper JSONQL adapter. The schema depends on the mode.

**When Oracle is connected (BI pipeline),** the output includes the narrative and all BI metrics:

```json
{
  "narrative": "Data-driven summary of arrears risk, payment integrity, and bankruptcy risk.",
  "total_debt": 12500.0,
  "debt_30_days": 4000.0,
  "debt_60_days": 3500.0,
  "debt_over_60": 5000.0,
  "large_bill_count": 12,
  "duplicate_payment_account_count": 2,
  "duplicate_payment_example_amt": 150.0,
  "bankruptcy_alert_count": 1,
  "bankruptcy_pym_amt": 75.0
}
```

- **narrative** (string): Senior BI Analyst narrative; map to the Summary Band text field.
- **total_debt**, **debt_30_days**, **debt_60_days**, **debt_over_60** (number): Arrearage aging buckets.
- **large_bill_count** (number): Count of bills over $500.
- **duplicate_payment_account_count** (number): Accounts with potential duplicate payment.
- **duplicate_payment_example_amt** (number): Example amount for duplicate flag.
- **bankruptcy_alert_count** (number): Bankruptcy-flagged accounts with payments in window.
- **bankruptcy_pym_amt** (number): Total payment amount on those accounts.

When **RISK_DATA_ENABLED=1**, the output also includes Risk Data metrics (used for "Unresolved Debt on Canceled Service," "Suspense Account Alert," "Service delay" in the narrative): **revenue_leakage_acct_count**, **revenue_leakage_total_amt**; **liquidity_pending_amt**, **liquidity_pending_count_48h**; **liquidity_unfrozen_amt**, **liquidity_unfrozen_count_48h**; **stale_pending_sa_count**.

**When using CSV or --mock (usage pipeline),** the output is:

```json
{
  "narrative": "Your bill increased by $30 due to high AC usage during the heatwave.",
  "current_amount": 150.0,
  "prior_amount": 120.0,
  "amount_delta": 30.0,
  "percent_change": 25.0
}
```

- **narrative** (string): 2-sentence bill summary; map to the Summary Band.
- **current_amount**, **prior_amount**, **amount_delta**, **percent_change** (number): Usage KPIs.

Ensure the JSONQL Data Adapter in Jaspersoft Studio maps the field names you use to the report parameters or fields. For BI reports, see [jasper-bi-reports.md](jasper-bi-reports.md).

## Rate Limits

- **OpenAI:** If you hit rate limits, wait and retry or use a higher tier. You can switch to a different `OPENAI_MODEL` (e.g. `gpt-4o-mini` for lower cost).
- **Gemini (if used):** If you see **"Resource Exhausted" (429)**, wait the time suggested or enable billing in [Google AI Studio](https://aistudio.google.com) for higher limits.

## Governance When Using Live Oracle Data

When you later connect `fetch_usage.py` to live Oracle C2M (instead of CSV), apply Origin’s mandatory safety filters in every query:

- **Financial facts:** `FREEZE_SW = 'Y'`
- **Active accounts:** `SA_STATUS_FLG = '20'`

See `docs/semantic-layer.md` and `sql/governance_snippets.sql` for exact snippets and date-window rules.

## Testing the BI Queries (No AI, No DB Changes)

To verify that the three BI queries return the right data **without** calling the AI or writing any files, run:

```bash
python -m pipeline.test_queries
```

This connects to Oracle (using `.env`), runs the same three governed **SELECT** queries used by the pipeline, and prints row counts, column names, and the first few rows of each result, plus the aggregated metrics that would be sent to the AI. Use it to validate schema and data before running the full pipeline. No database changes are made.

## Data validation and table verification

Before the BI pipeline runs, **validate_data_health()** checks that core C2M tables have recent data (e.g. CI_FT rows with CRE_DTTM in the last 7 days, active CI_SA, recent payments). If any check fails, the pipeline returns a **"No Data Found"** payload: a narrative stating that core tables appear empty or stale and zeroed metrics, so the AI does not summarize empty or legacy data.

To audit **row counts and data freshness** for every table used by the governed SQL (CI_FT, CI_SA, CI_ACCT, CI_ACCT_ALERT, CI_PREM, CI_PER_NAME, etc.), run:

```bash
python -m pipeline.validate_tables
```

This prints total row count and MAX(CRE_DTTM) or MAX(LAST_UPDATE_DTTM) per table. Use it in your test environment to confirm you are hitting **live production tables**, not empty or legacy tables. If a table shows 0 rows or a very old MAX date, verify the correct production source in the CISADM schema and update the SQL constants in `fetch_usage.py` or the `sql/*.sql` files. See [semantic-layer.md](semantic-layer.md) and [database-connections.md](database-connections.md).

### Data Quality Profiling (validate_tables)

The script has been extended into a **Data Quality Profiling** tool that reports:

- **Metadata overrides:** Tables that showed N/A for dates now use explicit columns where applicable: CI_PER_NAME uses `MAX(VERSION)` (name-update activity), CI_PREM uses `CRE_DTTM` when present, CI_ACCT_PER uses `LAST_UPDATE_DTTM`. If an override column is missing in your build, the script falls back to discovery or N/A.
- **Balance reconciliation:** After the table list, a **Data quality** section runs a check that compares the sum of arrears buckets (DEBT_30_DAYS + DEBT_60_DAYS + DEBT_OVER_60) to TOTAL_DEBT (tolerance 0.01). Any mismatched rows are reported so the Arrearage Narrative is not based on inconsistent data. Optionally you can wire this check into `validate_data_health()` in `fetch_usage.py` to warn or fail the pipeline when reconciliation fails.
- **ARS_DT null density:** Percentage of CI_FT rows (arrears population) with ARS_DT IS NULL. High null density means aging reports may under-report debt.
- **Orphan SA check:** Count of active service agreements (SA_STATUS_FLG in '20','30','40') that have no matching CI_FT rows under the same arrears filters. These are “new or unbilled” SAs; the AI can use this to say “This account is new and has no billing history yet” when NLQ returns an account with SAs but no financial transactions. An optional follow-up is to add a governed query (e.g. `sql/orphan_sa_by_acct.sql`) and call it from `fetch_bi_slice_for_account()` when arrears are empty for an account, to tailor the NLQ narrative.
- **Sample shape:** For each table, the script runs a 3-row sample and prints only the **column names** (no row values), so you can confirm the data shape matches what Jaspersoft and the pipeline expect.

## Natural Language Query (NLQ)

The pipeline includes a **RAG-based Natural Language Query** feature: users ask in plain language (e.g. “What is the status of Account 2927873805?”), and the system returns a data-grounded answer. All data comes from **governed SQL only**; the AI never writes or generates queries.

**Flow:** Intent classification (and optional regex for account numbers) → resolve entity to ACCT_ID (account, premise/address, or customer name) → retrieve one account’s metrics via parameterized governed SQL → generate narrative with a **guardrail** (answer only from provided data; if no data, say “I do not have access to that specific record”).

**CLI (testing and Jaspersoft):**

```bash
python -m pipeline.nlq "What is the status of Account 2927873805?"
```

Output is JSON: `narrative`, `acct_id`, `metrics`, `resolved_from`. Jaspersoft can invoke this script with a report parameter (e.g. account number or question) and use the returned narrative in the Summary Band.

**HTTP API (integrated search bar):**

From the repo root, run:

```bash
uvicorn api.nlq_server:app --reload
```

Then `POST /nlq` with body `{"query": "What is the status of Account 2927873805?"}` or **GET** `/nlq?query=...` (for Jaspersoft JSONQL). Response: `{"narrative": "...", "acct_id": ..., "metrics": {...}, "resolved_from": "acct"}`. Optional: set `NLQ_API_KEY` in `.env` and send header `X-API-Key` on `/nlq` requests; see [jasper-bi-reports.md](jasper-bi-reports.md).

**Premise and name resolution:** Premise/address and customer-name lookups use governed SQL in `sql/premise_to_acct_mapping.sql` (CI_PREM + CI_SA via CHAR_PREM_ID; ADDRESS1/ADDRESS1_UPR) and `sql/customer_name_to_acct.sql` (CI_PER_NAME + CI_ACCT_PER; ENTITY_NAME_UPR, PRIM_NAME_SW, MAIN_CUST_SW). Run these queries against your test environment to ensure they return the expected ACCT_ID(s). If your schema uses different column names (e.g. PREM_ID instead of CHAR_PREM_ID, ADDR_LINE_1 instead of ADDRESS1, FULL_NAME instead of ENTITY_NAME), adjust the SQL in those files and in `fetch_usage.py`. See [database-connections.md](database-connections.md).

## Prompt

The utility-analyst prompt includes usage amounts, **KPIs** (amount delta and percent change), and weather. The model (OpenAI or Gemini) returns **JSON** with a single key `narrative` so the output is valid for Jaspersoft. It is defined in `pipeline/generate_narrative.py`; you can adjust it there or extend it (e.g. via a config file) for different tones or locales.
