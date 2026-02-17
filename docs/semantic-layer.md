# Origin C2M Semantic Layer and Governance

This document defines **how we query Oracle C2M** for reporting and AI. Applying these rules ensures one version of the truth, accurate "Active Customer" and financial metrics, and stable performance on multi-million row tables.

## Read-only: No Database Changes

**The pipeline and all reporting queries must never modify the database.** Only **SELECT** statements are allowed. No INSERT, UPDATE, DELETE, MERGE, or DDL (CREATE, ALTER, DROP, TRUNCATE) may be run against C2M by this project. All SQL in `pipeline/queries.py`, `pipeline/fetch_usage.py`, and `sql/*.sql` is read-only. When adding new queries, keep them SELECT-only so testing and production runs cannot alter data. No query may use `SELECT *`; use explicit column lists only.

## Governance Rules

### 1. Blank Strings (C2M Space-Filled Nulls)

C2M often stores nulls as spaces. Normalize for reporting and AI so the semantic layer does not treat blank strings as values.

**Pattern:** Use `NULLIF(TRIM(column), '')` for any string column that may be space-filled.

**Example:**

```sql
NULLIF(TRIM(customer_name), '')     AS customer_name,
NULLIF(TRIM(sa_status_flg), '')   AS sa_status_flg
```

Use this in SELECT lists and in WHERE conditions when comparing to empty or unknown values.

### 2. Safety Filters

Apply these filters in **every** C2M query or Jaspersoft Domain that touches the relevant tables.

| Context | Filter | Purpose |
|--------|--------|--------|
| Financial facts | `FREEZE_SW = 'Y'` | Only use frozen, audited financial data |
| Active accounts | `SA_STATUS_FLG = '20'` | Restrict to active service points; avoid closed/cancelled |

**Example (financial):**

```sql
FROM ci_bseg
WHERE FREEZE_SW = 'Y'
```

**Example (active accounts):**

```sql
FROM ci_sa
WHERE SA_STATUS_FLG = '20'
```

Combine with blank-string normalization where the flag is a string column:

```sql
WHERE NULLIF(TRIM(SA_STATUS_FLG), '') = '20'
```

### 3. Relevant Data: Active and Not Paid Off

For **arrears and debt** (and any metric that should reflect *current* exposure), use only **relevant** rows:

- **Active service agreements only:** Use `NULLIF(TRIM(SA.SA_STATUS_FLG), '') = '20'`. Do not include closed/cancelled SAs (e.g. 30, 40) so metrics reflect only active accounts.
- **Outstanding balance only:** Exclude financial rows that are already paid or not in arrears:
  - CI_FT arrears: `FREEZE_SW = 'Y'`, `NOT_IN_ARS_SW = 'N'`, `FT_TYPE_FLG NOT IN ('PS', 'PX')`, and **`ARS_DT IS NOT NULL`** (valid arrears date; excludes cleared/void).
  - After aggregation, keep only groups with **`HAVING SUM(CUR_AMT) > 0`** so paid-off accounts do not appear.

Apply the same idea across workstreams: **billing, cashiering, meter, customer ops, new services, finance, debt management, field operations** should restrict to **active SAs** (and, where applicable, frozen/valid facts and date windows) so reports and AI narratives use only relevant, accurate data.

### 3b. Multi-Layer Validation (Source of Truth)

- **Arrears (CI_FT):** Always use **FREEZE_SW = 'Y'** so only frozen, audited rows are included (exclude in-progress or canceled adjustments). Keep **NOT_IN_ARS_SW = 'N'** so transactions explicitly excluded from arrears aging are omitted. Use **HAVING SUM(FT.CUR_AMT) > 0** so paid-off or zero balances are not reported.
- **Temporal validation:** Use **BILL_CYC_CD** (from CI_ACCT) where available to decide billing-gap lookback (e.g. monthly → 35 days, quarterly → 95 days). Compare **MAX(FT.CRE_DTTM)** to the last **F1_BATCH_RUN** end time to flag System Latency Risk when data is older than the last successful batch.
- **SmartCity tenant isolation:** When **F1_BUS_OBJ** (or F1_BUS_OBJ_L / F1_BUS_OBJ_STATUS_L) is available, join CI_SA to it to verify the "Standard Life Cycle" matches the expected SaaS behavior for that tenant (e.g. one city may use SA_STATUS_FLG = '20' for standard active; another may use custom life-cycle states). This keeps reporting correct across multiple clients.

### 4. Performance: Mandatory Filter Windows

Large C2M fact tables (e.g. usage, billing events) must be restricted by time to avoid full scans and timeouts.

**Rule:** Enforce a mandatory filter window (e.g. **90-day** facts) on date columns.

**Example:**

```sql
WHERE bill_dt >= ADD_MONTHS(TRUNC(SYSDATE), -3)
  AND bill_dt <  TRUNC(SYSDATE) + 1
```

Adjust the window (e.g. 30, 60, 90 days) per report and document it in the report or Domain.

## Governed Objects (Reference)

Use the following as a checklist when building queries or Jasper Domains.

| Object / Area | Key filters / normalization |
|---------------|-----------------------------|
| `CI_BSEG` (billing segments) | `FREEZE_SW = 'Y'`; date window on fact dates |
| `CI_SA` (service agreements) | `SA_STATUS_FLG = '20'`; `NULLIF(TRIM(...), '')` on string flags |
| Usage / meter facts | Date window (e.g. 90 days); link to active SA only |
| Customer / account dimensions | `NULLIF(TRIM(column), '')` on name/address/status fields |

## Nine Workstreams and Source-of-Truth Tables

The BI pipeline and NLQ assistant map each functional area to core "Source of Truth" tables. Run `python -m pipeline.validate_tables` to confirm your database user has SELECT on all of these (including D1 tables when present).

| Workstream | Source-of-truth tables | Ground-truth check | NLQ intent |
|------------|------------------------|--------------------|------------|
| **Billing & Rates** | CI_BSEG, CI_BILL, CI_FT, CI_RS_L | FREEZE_SW = 'Y'; date window | BILLING_LOOKUP |
| **Cashiering** | CI_PAY_EVENT, CI_PAY_TNDR, CI_DEP_CTL | TNDR_STATUS_FLG = '25' (Valid) for bank reconciliation | DEPOSIT_LOOKUP |
| **Meter Operations** | D1_DVC, D1_DVC_CFG, D1_INSTALL_EVT, CI_SP | D1 or CI_SP.INSTALL_DT fallback | METER_LOOKUP |
| **Customer Operations** | CI_ACCT, CI_PER_NAME, CI_ACCT_ALERT | Entity resolution and alert flags | CUSTOMER_ALERTS |
| **New Services** | CI_SA (status 10/20), CI_SP_CHAR | SA_STATUS_FLG = '10' (Pending) for pipeline view | NEW_SERVICES_LOOKUP |
| **Finance** | CI_FT_GL, CI_FT_PROC | GL_DISTRIB_STATUS for revenue vs GL | GL_LOOKUP |
| **Common** | CI_PREM, CI_LOOKUP_VAL | Shared address and status descriptions | (used by premise/entity resolution) |
| **Debt Management** | CI_ACCT (COLL_CL_CD, CR_REVIEW_DT), CI_FT | Collection class and credit review date | DEBT_MGMT_LOOKUP |
| **Field Operations** | CI_SP (INSTALL_DT, SP_STATUS_FLG) | Service point install and status | FIELD_OPS_LOOKUP |

- **Schema:** CI_* tables live under schema **CISADM**; device/meter tables (D1_DVC, D1_DVC_CFG, D1_INSTALL_EVT) use schema **D1** (adjust if your C2M uses a different owner).
- **Source of truth:** Table and column names align with **Domain Designs.xlsx** (e.g. D1_DVC = Device, D1_DVC_CFG = Device Configuration, D1_INSTALL_EVT = Install Event; CI_SP uses SP_STATUS_FLG).
- **Queries:** All workstream SQL is in `pipeline/queries.py` with explicit column lists. The NLQ router in `pipeline/nlq.py` maps intents (e.g. "meter", "GL", "deposit") to the corresponding governed query.

### Audit Mode (Risk Data)

Differentiate **Clean Data** (for financial statements) from **Risk Data** (for operational monitoring and Senior Data Auditor logic):

| Use | When | Filters / logic |
|-----|------|------------------|
| **Clean Data** | Reporting, financial statements, standard dashboards | `FREEZE_SW = 'Y'`, active SAs (`SA_STATUS_FLG = '20'`), governed arrears (e.g. `NOT_IN_ARS_SW = 'N'`, `ARS_DT IS NOT NULL`). |
| **Risk Data** | Audit mode: revenue leakage, cash flow bottleneck, service initiation | Canceled SAs (`SA_STATUS_FLG = '70'`) with outstanding frozen CI_FT; pending/unfrozen payments (e.g. `PAY_STATUS_FLG = 'P'`, `CI_FT.FREEZE_SW = 'N'`); pending SAs (`SA_STATUS_FLG = '10'`) with `START_DT` in the past. |

- **Toggle:** Set **`RISK_DATA_ENABLED=1`** (or `true`) in `.env` to run Risk Data queries. The pipeline then runs Revenue Leakage (canceled SA + unresolved debt), Liquidity Risk (pending payments and unfrozen CI_FT), and Stale Pending SA, and merges counts/amounts into the BI summary. The AI narrative and Business Snapshot will include "Unresolved Debt on Canceled Service," "Suspense Account Alert," and "Service delay detected: … check Field Task status in F1_TSK" when applicable. See `docs/pipeline.md` and `sql/governance_snippets.sql` for status constants.

### Domain Designs for client insights

**Domain Designs.xlsx** is the source of truth for table names and descriptions. To improve AI narratives and client insights:

1. **Metadata extraction:** Run `python scripts/refresh_domain_metadata.py` from the repo root (requires `pandas` and `openpyxl`). This reads the workbook and writes **`output/domain_designs_metadata.json`** (table descriptions, Summary sheet, and justification hints).
2. **Narrative context:** `pipeline/domain_context.py` loads that JSON and provides `get_workstream_table_descriptions()` and `get_insight_hints_for_workstream()`. `generate_narrative.py` appends the workstream table descriptions to the BI and NLQ system prompts so the model can attribute insights to the correct domain (e.g. "From meter operations...", "GL distribution...").
3. **After workbook changes:** Re-run `scripts/refresh_domain_metadata.py` so BI/NLQ use the latest table descriptions and hints.
4. **Justification / Designer Notes:** `domain_context.get_semantic_layer_prompt_suffix()` injects Designer Notes and workstream justification hints from the workbook into the AI system prompt so the model understands business context (e.g. why D1_INSTALL_EVT matters for device history).

### Workstream Health Matrix and Data Currency Risk

`python -m pipeline.validate_tables` runs a **Workstream Health Matrix**: for each workstream it checks whether the primary Source of Truth table has had a record created/frozen in the **last 7 days**. If not, that workstream is flagged as **Data Currency Risk**. Results are written to **`output/workstream_health.json`**. When generating BI or NLQ narratives, `generate_narrative.py` reads this file and, if any workstream is stale, adds a line to the user prompt so the AI can alert the client (e.g. "Consider flagging that Finance data has had no recent activity").

### Cross-Workstream NLQ

Questions that mention multiple workstreams (e.g. *"Show me the meter status and last payment for Account 2927873805"*) trigger **cross-workstream** routing: the NLQ pipeline fetches the BI slice plus all matching workstream slices (Meter Operations and Cashiering in that example) and passes combined `workstream_slices` to the narrative generator so the answer attributes insights by source (e.g. "From meter operations..."; "From cashiering...").

### After validate_tables: full functionality checklist

Once `python -m pipeline.validate_tables` runs successfully, use this to reach full functionality:

| What you see | What’s done / what to do |
|--------------|--------------------------|
| **D1.D1_DVC / D1_INSTALL_EVT not present** | Meter Operations uses a **CI_SP fallback**: `fetch_meter_ops_slice` queries `CI_SP.INSTALL_DT` and `SP_STATUS_FLG` by account when D1 tables are missing. Meter NLQ and cross-workstream (e.g. “meter status and last payment”) work without D1. |
| **CI_BSEG without RS_CD** | Billing uses **QUERY_BILLING_BSEG_BILL** (BSEG → BILL only). The pipeline does not require BSEG.RS_CD. Rate schedule lookup remains **CI_RS_L** separately. |
| **new_services / common “invalid identifier”** | Health matrix uses **START_DT** for CI_SA and **no date column** for CI_PREM (common). Re-run `validate_tables` after pulling the latest `queries.WORKSTREAM_HEALTH`. |
| **Balance reconciliation mismatches** | Expected when rounding or adjustments differ. Document as known; no pipeline change required. |
| **Orphan SAs (no CI_FT rows)** | Informational. Active SAs with no financial rows; no code change required. |

Recommended after validation: run **`python -m pipeline.nlq "Show me the meter status and last payment for Account &lt;acct_id&gt;"`** with a real account to confirm meter (CI_SP fallback) and cashiering slices and narrative.

### Next steps to further the pipeline

1. **Partial workstream data:** When a question touches multiple workstreams (e.g. meter + payment) but only some slices return data (e.g. cashiering yes, meter no), the NLQ prompt instructs the model to answer from the data that *is* present and then state what is missing (e.g. "From cashiering, 1 payment totaling $92. I do not have meter status for this account."). Re-run the same NLQ to verify the improved narrative.
2. **Nine workstreams:** Debt Management (COLL_CL_CD, CR_REVIEW_DT) and Field Operations (CI_SP install/status) are implemented; use keywords "debt", "collections", "credit review" or "field operations", "service point" to trigger them.
3. **Health matrix display:** Workstreams with no date column (e.g. Common / CI_PREM) now show **—** in the Count (7d) column instead of total row count.
4. **Extend Domain Designs:** Add Debt Management and Field Operations table descriptions or designer notes in the workbook, then run **`python scripts/refresh_domain_metadata.py`** so the semantic layer includes them in prompts.

## Sample SQL Snippets

See **[../sql/governance_snippets.sql](../sql/governance_snippets.sql)** for copy-paste WHERE clauses and expressions. Use them in ad-hoc SQL, Jasper Domain SQL, or ETL so all stakeholders query C2M the same way.

## Select AI Profile (Database)

For AI-generated SQL (e.g. Select AI in Oracle), create a profile so the LLM is aware of C2M objects and naming:

```sql
BEGIN
  DBMS_CLOUD_AI.CREATE_PROFILE(
    profile_name => 'origin_billing_profile',
    attributes   => '{"provider": "oci", "object_list": ["<your_c2m_objects>"]}'
  );
END;
```

Complete `object_list` with the C2M schemas/tables your reports use. This reduces hallucination and keeps generated SQL aligned with governed objects and filters above.
