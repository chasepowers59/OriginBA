export type DatabaseQueryTemplate = {
  id: string;
  category: string;
  title: string;
  description: string;
  tip: string;
  sql: string;
  /** Hint for auto-chart: dimension column (label axis) */
  chartDimension?: string;
  /** Hint for auto-chart: measure column (value axis) */
  chartMeasure?: string;
  chartType?: "bar" | "line" | "horizontal";
  isCurrency?: boolean;
  sortTimeSeries?: boolean;
};

export const DATABASE_TIPS = [
  "Start with a starter query below — each one is tuned for the governed snapshot tables.",
  "Results load 50 rows at a time. Use Fetch next when you need more rows without waiting for the full result set.",
  "Add a date filter (last 6 months) to keep queries fast on large tables like FT and billed usage.",
  "Use BSEG_BILLED_USAGE for billed dollars; use BSEG_SQ_USAGE for quantity by unit of measure (UOM).",
  "Press Ctrl+Enter (⌘+Enter on Mac) to run the statement.",
  "Toggle Chart view when your result has categories and numbers — great for monthly trends or class breakdowns.",
  "Row count runs a full COUNT(*) and can be slow on big tables — use it when you really need the total.",
];

export const DATABASE_QUERY_TEMPLATES: DatabaseQueryTemplate[] = [
  {
    id: "snapshot_health",
    category: "Operations",
    title: "Snapshot freshness check",
    description: "Row counts and latest refresh time for the main reporting snapshots.",
    tip: "Helpful after a rollout. This scans whole tables and may take 15–30 seconds.",
    sql: `SELECT 'FT_RPT_CURR' AS snapshot_table,
       COUNT(*) AS row_count,
       MAX(load_dttm) AS last_refresh
FROM CISADM.FT_RPT_CURR
UNION ALL
SELECT 'BSEG_BILLED_USAGE_RPT_CURR', COUNT(*), MAX(load_dttm)
FROM CISADM.BSEG_BILLED_USAGE_RPT_CURR
UNION ALL
SELECT 'BSEG_SQ_USAGE_RPT_CURR', COUNT(*), MAX(load_dttm)
FROM CISADM.BSEG_SQ_USAGE_RPT_CURR
UNION ALL
SELECT 'D1_MSRMT_RPT_CURR', COUNT(*), MAX(load_dttm)
FROM CISADM.D1_MSRMT_RPT_CURR
UNION ALL
SELECT 'FT_GL_DISTRIBUTION_RPT_CURR', COUNT(*), MAX(load_dttm)
FROM CISADM.FT_GL_DISTRIBUTION_RPT_CURR
UNION ALL
SELECT 'D1_USAGE_RPT_CURR', COUNT(*), MAX(load_dttm)
FROM CISADM.D1_USAGE_RPT_CURR
UNION ALL
SELECT 'D1_USAGE_SCALAR_DTL_RPT_CURR', COUNT(*), MAX(load_dttm)
FROM CISADM.D1_USAGE_SCALAR_DTL_RPT_CURR`,
  },
  {
    id: "ft_monthly_revenue",
    category: "Finance",
    title: "FT dollars by month (last 6 months)",
    description: "Monthly financial transaction count and current amount totals.",
    tip: "Uses ACCOUNTING_DT. Switch to payoff amount only when payoff exposure is the question.",
    sql: `SELECT TRUNC(accounting_dt, 'MM') AS bill_month,
       COUNT(*) AS ft_count,
       SUM(cur_amt) AS total_cur_amt
FROM CISADM.FT_RPT_CURR
WHERE accounting_dt >= ADD_MONTHS(TRUNC(SYSDATE), -6)
GROUP BY TRUNC(accounting_dt, 'MM')
ORDER BY 1`,
    chartDimension: "BILL_MONTH",
    chartMeasure: "TOTAL_CUR_AMT",
    chartType: "line",
    isCurrency: true,
    sortTimeSeries: true,
  },
  {
    id: "ft_by_type",
    category: "Finance",
    title: "FT volume and dollars by transaction type",
    description: "Which FT types drive activity and dollars in the last 90 days.",
    tip: "Filter GL distribution status in the WHERE clause for posting health views.",
    sql: `SELECT ft_type_flg_desc AS ft_type,
       COUNT(*) AS ft_count,
       SUM(cur_amt) AS total_cur_amt
FROM CISADM.FT_RPT_CURR
WHERE accounting_dt >= TRUNC(SYSDATE) - 90
GROUP BY ft_type_flg_desc
ORDER BY total_cur_amt DESC`,
    chartDimension: "FT_TYPE",
    chartMeasure: "TOTAL_CUR_AMT",
    chartType: "horizontal",
    isCurrency: true,
  },
  {
    id: "ft_gl_status",
    category: "Finance",
    title: "Transactions by GL posting status",
    description: "Distribution of FT rows by GL distribution status (last 90 days).",
    tip: "Pair with FT type for an operations monitor of undistributed transactions.",
    sql: `SELECT gl_distrib_status_desc AS gl_status,
       COUNT(*) AS ft_count,
       SUM(cur_amt) AS total_cur_amt
FROM CISADM.FT_RPT_CURR
WHERE accounting_dt >= TRUNC(SYSDATE) - 90
GROUP BY gl_distrib_status_desc
ORDER BY ft_count DESC`,
    chartDimension: "GL_STATUS",
    chartMeasure: "FT_COUNT",
    chartType: "bar",
  },
  {
    id: "billed_by_class",
    category: "Billing",
    title: "Billed revenue by customer class",
    description: "Total billed dollars (TOTAL_CALC_AMT) by customer class — last 6 months.",
    tip: "Segment grain — one row per bill segment. Do not sum TOTAL_BILL_SQ here for usage.",
    sql: `SELECT cust_cl_desc AS customer_class,
       COUNT(*) AS bill_segments,
       SUM(total_calc_amt) AS billed_amt
FROM CISADM.BSEG_BILLED_USAGE_RPT_CURR
WHERE bill_dt >= ADD_MONTHS(TRUNC(SYSDATE), -6)
GROUP BY cust_cl_desc
ORDER BY billed_amt DESC`,
    chartDimension: "CUSTOMER_CLASS",
    chartMeasure: "BILLED_AMT",
    chartType: "horizontal",
    isCurrency: true,
  },
  {
    id: "billed_by_cycle",
    category: "Billing",
    title: "Billed revenue by bill cycle",
    description: "Billed dollars grouped by bill cycle for recent billing periods.",
    tip: "Useful for cycle-level billing health and revenue comparisons.",
    sql: `SELECT bill_bill_cyc_desc AS bill_cycle,
       COUNT(*) AS bill_segments,
       SUM(total_calc_amt) AS billed_amt
FROM CISADM.BSEG_BILLED_USAGE_RPT_CURR
WHERE bill_dt >= ADD_MONTHS(TRUNC(SYSDATE), -6)
GROUP BY bill_bill_cyc_desc
ORDER BY billed_amt DESC`,
    chartDimension: "BILL_CYCLE",
    chartMeasure: "BILLED_AMT",
    chartType: "bar",
    isCurrency: true,
  },
  {
    id: "usage_by_uom",
    category: "Billing",
    title: "Billed quantity by unit of measure",
    description: "SQ usage snapshot — quantity by UOM for the last 6 months.",
    tip: "This is the correct table for billed quantity. Filter UOM_DESC for a specific commodity.",
    sql: `SELECT uom_desc AS unit_of_measure,
       COUNT(*) AS row_count,
       SUM(total_bill_sq) AS total_quantity
FROM CISADM.BSEG_SQ_USAGE_RPT_CURR
WHERE bill_dt >= ADD_MONTHS(TRUNC(SYSDATE), -6)
GROUP BY uom_desc
ORDER BY total_quantity DESC`,
    chartDimension: "UNIT_OF_MEASURE",
    chartMeasure: "TOTAL_QUANTITY",
    chartType: "bar",
  },
  {
    id: "measurement_monthly",
    category: "Meter ops",
    title: "Meter readings by month",
    description: "Monthly measurement row counts and summed register values.",
    tip: "Uses D1_MSRMT_RPT_CURR. Narrow by date for faster runs on large registers.",
    sql: `SELECT TRUNC(msrmt_dttm, 'MM') AS measure_month,
       COUNT(*) AS reading_count,
       SUM(msrmt_val) AS total_msrmt_val
FROM CISADM.D1_MSRMT_RPT_CURR
WHERE msrmt_dttm >= ADD_MONTHS(TRUNC(SYSDATE), -6)
GROUP BY TRUNC(msrmt_dttm, 'MM')
ORDER BY 1`,
    chartDimension: "MEASURE_MONTH",
    chartMeasure: "READING_COUNT",
    chartType: "line",
    sortTimeSeries: true,
  },
  {
    id: "gl_by_account",
    category: "Finance",
    title: "GL distribution by account (last 6 months)",
    description: "Top GL accounts by distribution amount from the GL detail snapshot.",
    tip: "Use FT_GL_DISTRIBUTION for GL line detail — not FT_RPT_CURR header totals.",
    sql: `SELECT gl_acct AS gl_account,
       COUNT(*) AS distribution_lines,
       SUM(gl_amount) AS total_gl_amt
FROM CISADM.FT_GL_DISTRIBUTION_RPT_CURR
WHERE accounting_dt >= ADD_MONTHS(TRUNC(SYSDATE), -6)
GROUP BY gl_acct
ORDER BY total_gl_amt DESC`,
    chartDimension: "GL_ACCOUNT",
    chartMeasure: "TOTAL_GL_AMT",
    chartType: "horizontal",
    isCurrency: true,
  },
  {
    id: "usage_summary",
    category: "Meter ops",
    title: "Usage rows by month",
    description: "Monthly usage snapshot activity from D1_USAGE_RPT_CURR.",
    tip: "Scalar detail lives in D1_USAGE_SCALAR_DTL_RPT_CURR when you need line-level quantities.",
    sql: `SELECT TRUNC(u.start_dttm, 'MM') AS usage_month,
       COUNT(*) AS detail_rows,
       SUM(s.final_quantity) AS total_quantity
FROM CISADM.D1_USAGE_SCALAR_DTL_RPT_CURR s
JOIN CISADM.D1_USAGE_RPT_CURR u ON u.d1_usage_id = s.d1_usage_id
WHERE u.start_dttm >= ADD_MONTHS(TRUNC(SYSDATE), -6)
GROUP BY TRUNC(u.start_dttm, 'MM')
ORDER BY 1`,
    chartDimension: "USAGE_MONTH",
    chartMeasure: "TOTAL_QUANTITY",
    chartType: "line",
    sortTimeSeries: true,
  },
  {
    id: "peek_ft",
    category: "Quick look",
    title: "Preview FT rows",
    description: "First 50 financial transaction rows — good for exploring columns.",
    tip: "Fast starter query. Edit the WHERE clause to narrow by date or account.",
    sql: `SELECT ft_id,
       accounting_dt,
       ft_type_flg_desc,
       cur_amt,
       gl_distrib_status_desc,
       acct_mgmt_grp_desc
FROM CISADM.FT_RPT_CURR
WHERE accounting_dt >= ADD_MONTHS(TRUNC(SYSDATE), -1)
ORDER BY accounting_dt DESC`,
  },
];

export const DATABASE_TEMPLATE_CATEGORIES = [
  "All",
  ...Array.from(new Set(DATABASE_QUERY_TEMPLATES.map((t) => t.category))),
];

// ---------------------------------------------------------------------------
// WAREHOUSE templates — the dbt reporting canvases (Postgres). Column names are
// the governed Title-Case contract, verified against output/catalog_dbt.json;
// never guess a name here, the validator holds queries to the real ones.
// ---------------------------------------------------------------------------

export const WAREHOUSE_TIPS = [
  "You are querying the governed reporting canvases (reporting.rpt_*) — the same tables every dashboard reads.",
  "Column names are business names in double quotes: \"Billed Amount\", \"Main Customer Name\".",
  "Flags are real booleans — filter with WHERE \"Is Completed\" or WHERE NOT \"Has Installed Device\".",
  "Results load 50 rows at a time. Use Fetch next when you need more rows without waiting for the full result set.",
  "Add a date filter (last 6 months) to keep queries fast on the big canvases like rpt_financial_txn.",
  "Press Ctrl+Enter (⌘+Enter on Mac) to run the statement.",
  "Toggle Chart view when your result has categories and numbers — great for monthly trends or class breakdowns.",
];

export const WAREHOUSE_QUERY_TEMPLATES: DatabaseQueryTemplate[] = [
  {
    id: "wh_canvas_freshness",
    category: "Operations",
    title: "Canvas freshness check",
    description: "Row counts for the core reporting canvases, plus the warehouse's refresh watermark.",
    tip: "\"Load Date/Time\" on rpt_financial_txn is the CDC watermark — the same marker the Data Quality page keys its acks to.",
    sql: `SELECT 'rpt_financial_txn' AS canvas, COUNT(*) AS row_count, MAX("Load Date/Time") AS last_refresh
FROM rpt_financial_txn
UNION ALL
SELECT 'rpt_bill_segment', COUNT(*), NULL FROM rpt_bill_segment
UNION ALL
SELECT 'rpt_payment_tender', COUNT(*), NULL FROM rpt_payment_tender
UNION ALL
SELECT 'rpt_measurement', COUNT(*), NULL FROM rpt_measurement
UNION ALL
SELECT 'rpt_gl', COUNT(*), NULL FROM rpt_gl`,
  },
  {
    id: "wh_ft_monthly",
    category: "Finance",
    title: "FT dollars by month (last 6 months)",
    description: "Monthly financial transaction count and current amount totals.",
    tip: "Frozen FTs only — the canvas flag states the lifecycle basis.",
    sql: `SELECT date_trunc('month', "Accounting Date") AS month,
       COUNT(*) AS ft_count,
       SUM("Current Amount") AS total_current_amount
FROM rpt_financial_txn
WHERE "Accounting Date" >= date_trunc('month', current_date) - interval '6 months'
  AND "Is Frozen"
GROUP BY 1
ORDER BY 1`,
    chartDimension: "month",
    chartMeasure: "total_current_amount",
    chartType: "line",
    isCurrency: true,
    sortTimeSeries: true,
  },
  {
    id: "wh_ft_by_type",
    category: "Finance",
    title: "FT volume and dollars by transaction type",
    description: "Which FT types drive activity and dollars in the last 90 days.",
    tip: "Add \"GL Distribution Status\" to the SELECT for a posting-health view.",
    sql: `SELECT "FT Type" AS ft_type,
       COUNT(*) AS ft_count,
       SUM("Current Amount") AS total_current_amount
FROM rpt_financial_txn
WHERE "Accounting Date" >= current_date - 90
GROUP BY "FT Type"
ORDER BY total_current_amount DESC`,
    chartDimension: "ft_type",
    chartMeasure: "total_current_amount",
    chartType: "horizontal",
    isCurrency: true,
  },
  {
    id: "wh_billed_by_class",
    category: "Billing",
    title: "Billed revenue by customer class",
    description: "Total billed dollars by customer class — last 6 months.",
    tip: "Segment grain — one row per bill segment. \"Billed Amount\" is the calc-line total, the correct billed figure.",
    sql: `SELECT "Customer Class" AS customer_class,
       COUNT(*) AS bill_segments,
       SUM("Billed Amount") AS billed_amount
FROM rpt_bill_segment
WHERE "Bill Date" >= current_date - interval '6 months'
GROUP BY "Customer Class"
ORDER BY billed_amount DESC`,
    chartDimension: "customer_class",
    chartMeasure: "billed_amount",
    chartType: "horizontal",
    isCurrency: true,
  },
  {
    id: "wh_billed_by_cycle",
    category: "Billing",
    title: "Billed revenue by bill cycle",
    description: "Billed dollars grouped by bill cycle for recent billing periods.",
    tip: "Useful for cycle-level billing health and revenue comparisons.",
    sql: `SELECT "Bill Cycle" AS bill_cycle,
       COUNT(*) AS bill_segments,
       SUM("Billed Amount") AS billed_amount
FROM rpt_bill_segment
WHERE "Bill Date" >= current_date - interval '6 months'
GROUP BY "Bill Cycle"
ORDER BY billed_amount DESC`,
    chartDimension: "bill_cycle",
    chartMeasure: "billed_amount",
    chartType: "bar",
    isCurrency: true,
  },
  {
    id: "wh_charges_by_description",
    category: "Billing",
    title: "Billed dollars by charge description",
    description: "Which charge lines carry the revenue — calc-line grain.",
    tip: "The line-level detail behind every bill segment; filter with ILIKE '%tax%' to profile tax lines.",
    sql: `SELECT "Charge Description" AS charge,
       COUNT(*) AS line_count,
       SUM("Billed Amount") AS billed_amount
FROM rpt_billed_charge
GROUP BY "Charge Description"
ORDER BY billed_amount DESC
LIMIT 25`,
    chartDimension: "charge",
    chartMeasure: "billed_amount",
    chartType: "horizontal",
    isCurrency: true,
  },
  {
    id: "wh_measurements_monthly",
    category: "Meter ops",
    title: "Measurements by month",
    description: "Monthly measurement counts, with the estimated share.",
    tip: "\"Is Estimated Measurement\" is a real boolean — a rising estimated share is the complaint zone.",
    sql: `SELECT date_trunc('month', "Measurement Date/Time") AS month,
       COUNT(*) AS measurement_count,
       COUNT(*) FILTER (WHERE "Is Estimated Measurement") AS estimated_count
FROM rpt_measurement
WHERE "Measurement Date/Time" >= current_date - interval '6 months'
GROUP BY 1
ORDER BY 1`,
    chartDimension: "month",
    chartMeasure: "measurement_count",
    chartType: "line",
    sortTimeSeries: true,
  },
  {
    id: "wh_gl_by_account",
    category: "Finance",
    title: "GL distribution by account (last 6 months)",
    description: "Top GL accounts by distribution amount from the GL canvas.",
    tip: "Use rpt_gl for GL line detail — not the FT header totals.",
    sql: `SELECT "GL Account" AS gl_account,
       COUNT(*) AS distribution_lines,
       SUM("GL Amount") AS total_gl_amount
FROM rpt_gl
WHERE "Accounting Date" >= current_date - interval '6 months'
GROUP BY "GL Account"
ORDER BY total_gl_amount DESC`,
    chartDimension: "gl_account",
    chartMeasure: "total_gl_amount",
    chartType: "horizontal",
    isCurrency: true,
  },
  {
    id: "wh_stuck_bills",
    category: "Operations",
    title: "Bills stuck open over 30 days",
    description: "The billing engine's stuck-bill worklist, straight off rpt_bill.",
    tip: "Measured norm is p50 3.8 / p99 24.2 days open — 30+ is genuinely stuck.",
    sql: `SELECT "Bill ID", "Main Customer Name", "Bill Date", "Days Bill Open"
FROM rpt_bill
WHERE "Days Bill Open" > 30
ORDER BY "Days Bill Open" DESC`,
  },
  {
    id: "wh_peek_ft",
    category: "Quick look",
    title: "Preview financial transactions",
    description: "Recent financial transaction rows — good for exploring columns.",
    tip: "Fast starter query. Edit the WHERE clause to narrow by date or account.",
    sql: `SELECT "FT ID", "Accounting Date", "FT Type", "Current Amount",
       "GL Distribution Status", "Main Customer Name"
FROM rpt_financial_txn
WHERE "Accounting Date" >= current_date - interval '1 month'
ORDER BY "Accounting Date" DESC`,
  },
];

export type WorkspaceEngine = "postgres" | "oracle" | "oracle_dbt";

// The in-database shape (2026-08-28): the same governed rpt_* canvases, living in
// ORIGINBA_REPORTING inside the client's own Oracle instance. Columns keep their
// quoted Title-Case names; dates and row limits use Oracle idioms.
const ORACLE_DBT_QUERY_TEMPLATES: DatabaseQueryTemplate[] = [
  {
    id: "odbt_recent_fts",
    category: "Finance",
    title: "Recent financial transactions",
    description: "Frozen financial activity for the last month, newest first.",
    tip: "Edit the WHERE clause to narrow by date or account.",
    sql: `SELECT "FT ID", "Accounting Date", "FT Type", "Current Amount",
       "GL Distribution Status", "Main Customer Name"
FROM rpt_financial_txn
WHERE "Accounting Date" >= ADD_MONTHS(TRUNC(SYSDATE), -1)
ORDER BY "Accounting Date" DESC
FETCH FIRST 100 ROWS ONLY`,
  },
  {
    id: "odbt_billing_by_month",
    category: "Billing",
    title: "Billed amount by month",
    description: "Twelve months of billed segment revenue.",
    tip: "TRUNC(date, 'MM') is the Oracle month bucket.",
    sql: `SELECT TRUNC("Bill Date", 'MM') AS billing_month,
       COUNT(*) AS segments,
       SUM("Billed Amount") AS billed_amount
FROM rpt_bill_segment
WHERE "Bill Date" >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12)
GROUP BY TRUNC("Bill Date", 'MM')
ORDER BY billing_month`,
  },
  {
    id: "odbt_aged_debt",
    category: "Collections",
    title: "Aged receivables by bucket",
    description: "The arrears position straight off the aged balance canvas.",
    tip: "Buckets age by days past due, matching the CIS arrears zone.",
    sql: `SELECT COUNT(*) AS service_agreements,
       SUM("Current Balance") AS current_balance,
       SUM("Arrears 0-30 Days") AS bucket_0_30,
       SUM("Arrears 31-60 Days") AS bucket_31_60,
       SUM("Arrears 61-90 Days") AS bucket_61_90,
       SUM("Arrears 121+ Days") AS bucket_121_plus
FROM rpt_sa_aged_balance`,
  },
  {
    id: "odbt_payments",
    category: "Payments",
    title: "Payments by tender type",
    description: "Last 30 days of tenders, grouped by how customers paid.",
    tip: "Unqualified rpt_* names resolve to the governed reporting layer.",
    sql: `SELECT "Tender Type", COUNT(*) AS tenders, SUM("Tender Amount") AS amount
FROM rpt_payment_tender
WHERE "Payment Date" >= TRUNC(SYSDATE) - 30
GROUP BY "Tender Type"
ORDER BY amount DESC`,
  },
];

const ORACLE_DBT_TIPS: string[] = [
  "You are reading the governed reporting canvases inside this client's own Oracle instance -- the same tables the dashboards use, refreshed every 6 hours.",
  "Column names are quoted and Title Case: \"Account ID\", \"Accounting Date\".",
  "Use FETCH FIRST n ROWS ONLY (not LIMIT) and TRUNC/ADD_MONTHS for dates.",
  "Only the reporting layer is queryable; staging, core, and CISADM are fenced off.",
];

export function templatesForEngine(engine: WorkspaceEngine): DatabaseQueryTemplate[] {
  if (engine === "oracle_dbt") return ORACLE_DBT_QUERY_TEMPLATES;
  return engine === "postgres" ? WAREHOUSE_QUERY_TEMPLATES : DATABASE_QUERY_TEMPLATES;
}

export function tipsForEngine(engine: WorkspaceEngine): string[] {
  if (engine === "oracle_dbt") return ORACLE_DBT_TIPS;
  return engine === "postgres" ? WAREHOUSE_TIPS : DATABASE_TIPS;
}

export function categoriesForEngine(engine: WorkspaceEngine): string[] {
  return ["All", ...Array.from(new Set(templatesForEngine(engine).map((t) => t.category)))];
}
