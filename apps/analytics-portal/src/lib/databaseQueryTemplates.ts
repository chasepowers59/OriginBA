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
  "Start with a starter query below — each one is tuned for the governed canvass.",
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
    title: "Canvas freshness check",
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
    description: "SQ usage canvas — quantity by UOM for the last 6 months.",
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
    description: "Top GL accounts by distribution amount from the GL detail canvas.",
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
    description: "Monthly usage canvas activity from D1_USAGE_RPT_CURR.",
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
    id: "batch_run_status",
    category: "Operations",
    title: "Batch runs by status (last 7 days)",
    description:
      "Did last night's jobs land? Every batch run in the last week, by outcome, worst first.",
    tip:
      "RUN_STATUS is DECODED from CI_LOOKUP_VAL_L, never hand-written: 30 is Error and 40 is Complete, and a CASE that guessed otherwise once reported a failed batch as still running. Both sides are TRIMmed because these are CHAR columns.",
    sql: `SELECT TRIM(b.run_status)                       AS run_status_cd,
       NVL(TRIM(l.descr), '(unmapped status)')      AS run_status,
       COUNT(*)                                     AS runs,
       COUNT(DISTINCT TRIM(b.batch_cd))             AS distinct_jobs,
       MAX(b.end_dttm)                              AS latest_end
FROM CISADM.CI_BATCH_RUN b
LEFT JOIN CISADM.CI_LOOKUP_VAL_L l
       ON TRIM(l.field_name) = 'RUN_STATUS'
      AND TRIM(l.field_value) = TRIM(b.run_status)
WHERE b.batch_bus_dt >= TRUNC(SYSDATE) - 7
GROUP BY TRIM(b.run_status), TRIM(l.descr)
ORDER BY runs DESC`,
    chartDimension: "RUN_STATUS",
    chartMeasure: "RUNS",
    chartType: "bar",
  },
  {
    id: "vee_open_exceptions",
    category: "Meter ops",
    title: "Open VEE exceptions by rule",
    description:
      "Measurements that failed validation or estimation and are still open — the MDM worklist.",
    tip:
      "Severity and open/closed are decoded from CI_LOOKUP_VAL_L (D1IF Information, D1IS Issues, D1TM Terminate). Closed exceptions are history; the open ones are the work.",
    sql: `SELECT TRIM(e.vee_rule_cd)                       AS vee_rule,
       NVL(TRIM(s.descr), TRIM(e.excp_severity_flg)) AS severity,
       COUNT(*)                                      AS open_exceptions
FROM CISADM.D1_VEE_EXCP e
LEFT JOIN CISADM.CI_LOOKUP_VAL_L o
       ON TRIM(o.field_name) = 'OPEN_CLOSE_FLG'
      AND TRIM(o.field_value) = TRIM(e.open_close_flg)
LEFT JOIN CISADM.CI_LOOKUP_VAL_L s
       ON TRIM(s.field_name) = 'EXCP_SEVERITY_FLG'
      AND TRIM(s.field_value) = TRIM(e.excp_severity_flg)
WHERE TRIM(o.descr) = 'Open'
GROUP BY TRIM(e.vee_rule_cd), TRIM(s.descr), TRIM(e.excp_severity_flg)
ORDER BY open_exceptions DESC`,
    chartDimension: "VEE_RULE",
    chartMeasure: "OPEN_EXCEPTIONS",
    chartType: "horizontal",
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

export const WAREHOUSE_TIPS = [
  "You are querying the CISADM schema — the same tables you know from CIS. Unqualified names resolve there.",
  "Protected columns (MICR_ID, WEB_PASSWD, ALERT_INFO) are blocked, and SELECT * on CI_PAY_TNDR needs an explicit column list.",
  "Lowercase table names here (cisadm.ci_acct); dates use date_trunc('month', dt) and current_date - interval '6 months'.",
  "The Tables tab lists CISADM tables busiest-first, with a guide line for the core ones.",
  "Press Ctrl+Enter (⌘+Enter on Mac) to run the statement; results load 50 rows at a time.",
];

export const WAREHOUSE_QUERY_TEMPLATES: DatabaseQueryTemplate[] = [
  {
    id: "wh_accts_by_class",
    category: "Customers",
    title: "Accounts by customer class",
    description: "How the account base splits across customer classes.",
    tip: "cust_cl_cd is client-configured — join ci_cust_cl_l for the English description.",
    sql: `SELECT a.cust_cl_cd,
       l.descr AS customer_class,
       COUNT(*) AS accounts
FROM cisadm.ci_acct a
LEFT JOIN cisadm.ci_cust_cl_l l
  ON l.cust_cl_cd = a.cust_cl_cd AND l.language_cd = 'ENG'
GROUP BY a.cust_cl_cd, l.descr
ORDER BY accounts DESC`,
    chartDimension: "customer_class",
    chartMeasure: "accounts",
    chartType: "horizontal",
  },
  {
    id: "wh_ft_monthly",
    category: "Finance",
    title: "Frozen FT dollars by month (last 6 months)",
    description: "Monthly financial-transaction count and current amount, frozen FTs only.",
    tip: "freeze_sw = 'Y' is the frozen lifecycle basis — unfrozen FTs are still in flight.",
    sql: `SELECT date_trunc('month', accounting_dt) AS month,
       COUNT(*) AS ft_count,
       SUM(cur_amt) AS total_current_amount
FROM cisadm.ci_ft
WHERE freeze_sw = 'Y'
  AND accounting_dt >= date_trunc('month', current_date) - interval '6 months'
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
    title: "FT volume and dollars by type",
    description: "Which FT types (BS, PS, AD…) drive activity in the last 90 days.",
    tip: "BS/BX net against each other on a rebill; they do not disappear.",
    sql: `SELECT ft_type_flg,
       COUNT(*) AS ft_count,
       SUM(cur_amt) AS total_current_amount
FROM cisadm.ci_ft
WHERE freeze_sw = 'Y'
  AND accounting_dt >= current_date - 90
GROUP BY ft_type_flg
ORDER BY total_current_amount DESC`,
    chartDimension: "ft_type_flg",
    chartMeasure: "total_current_amount",
    chartType: "horizontal",
    isCurrency: true,
  },
  {
    id: "wh_bills_by_month",
    category: "Billing",
    title: "Bills completed by month",
    description: "Twelve months of completed-bill throughput.",
    tip: "bill_stat_flg = 'C' is Complete; 'P' bills are still pending.",
    sql: `SELECT date_trunc('month', bill_dt) AS month,
       COUNT(*) AS bills_completed
FROM cisadm.ci_bill
WHERE bill_stat_flg = 'C'
  AND bill_dt >= date_trunc('month', current_date) - interval '12 months'
GROUP BY 1
ORDER BY 1`,
    chartDimension: "month",
    chartMeasure: "bills_completed",
    chartType: "line",
    sortTimeSeries: true,
  },
  {
    id: "wh_frozen_bsegs",
    category: "Billing",
    title: "Bill segments by status",
    description: "The segment lifecycle at a glance — frozen, pending, cancelled.",
    tip: "bseg_stat_flg 50 = Frozen, 60 = Cancelled; pending states sit below 50.",
    sql: `SELECT bseg_stat_flg,
       COUNT(*) AS segments
FROM cisadm.ci_bseg
GROUP BY bseg_stat_flg
ORDER BY segments DESC`,
    chartDimension: "bseg_stat_flg",
    chartMeasure: "segments",
    chartType: "bar",
  },
  {
    id: "wh_payments_by_tender",
    category: "Payments",
    title: "Payments by tender type (last 30 days)",
    description: "How customers paid — cash, check, card — with dollar totals.",
    tip: "Columns are listed explicitly: SELECT * is blocked on ci_pay_tndr (protected columns).",
    sql: `SELECT t.tender_type_cd,
       COUNT(*) AS tenders,
       SUM(t.tender_amt) AS amount
FROM cisadm.ci_pay_tndr t
GROUP BY t.tender_type_cd
ORDER BY amount DESC`,
    chartDimension: "tender_type_cd",
    chartMeasure: "amount",
    chartType: "horizontal",
    isCurrency: true,
  },
  {
    id: "wh_sa_by_status",
    category: "Customers",
    title: "Service agreements by status",
    description: "The SA portfolio: active, stopped, closed.",
    tip: "sa_status_flg 20 = Active, 40 = Stopped, 60 = Closed, 70 = Reactivated.",
    sql: `SELECT s.sa_status_flg,
       COUNT(*) AS service_agreements
FROM cisadm.ci_sa s
GROUP BY s.sa_status_flg
ORDER BY service_agreements DESC`,
    chartDimension: "sa_status_flg",
    chartMeasure: "service_agreements",
    chartType: "bar",
  },
  {
    id: "wh_recent_fts",
    category: "Finance",
    title: "Recent financial transactions",
    description: "The latest frozen FTs, newest first.",
    tip: "Fast starter — edit the WHERE clause to narrow by account or SA.",
    sql: `SELECT ft_id, ft_type_flg, accounting_dt, cur_amt, tot_amt, sa_id
FROM cisadm.ci_ft
WHERE freeze_sw = 'Y'
ORDER BY accounting_dt DESC
LIMIT 100`,
  },
];

export type WorkspaceEngine = "postgres" | "oracle" | "oracle_dbt";

// The in-database shape (2026-08-28): the same governed rpt_* canvases, living in
// ORIGINBA_REPORTING inside the client's own Oracle instance. Columns keep their
// quoted Title-Case names; dates and row limits use Oracle idioms.
const ORACLE_DBT_QUERY_TEMPLATES: DatabaseQueryTemplate[] = [
  {
    id: "odbt_accts_by_class",
    category: "Customers",
    title: "Accounts by customer class",
    description: "How the account base splits across customer classes.",
    tip: "cust_cl_cd is client-configured — join CI_CUST_CL_L for the English description.",
    sql: `SELECT a.cust_cl_cd,
       l.descr AS customer_class,
       COUNT(*) AS accounts
FROM CI_ACCT a
LEFT JOIN CI_CUST_CL_L l
  ON l.cust_cl_cd = a.cust_cl_cd AND l.language_cd = 'ENG'
GROUP BY a.cust_cl_cd, l.descr
ORDER BY accounts DESC`,
    chartDimension: "customer_class",
    chartMeasure: "accounts",
    chartType: "horizontal",
  },
  {
    id: "odbt_ft_monthly",
    category: "Finance",
    title: "Frozen FT dollars by month (last 6 months)",
    description: "Monthly financial-transaction count and current amount, frozen FTs only.",
    tip: "freeze_sw = 'Y' is the frozen lifecycle basis.",
    sql: `SELECT TRUNC(accounting_dt, 'MM') AS month,
       COUNT(*) AS ft_count,
       SUM(cur_amt) AS total_current_amount
FROM CI_FT
WHERE freeze_sw = 'Y'
  AND accounting_dt >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -6)
GROUP BY TRUNC(accounting_dt, 'MM')
ORDER BY month`,
    chartDimension: "month",
    chartMeasure: "total_current_amount",
    chartType: "line",
    isCurrency: true,
    sortTimeSeries: true,
  },
  {
    id: "odbt_bills_by_month",
    category: "Billing",
    title: "Bills completed by month",
    description: "Twelve months of completed-bill throughput.",
    tip: "bill_stat_flg = 'C' is Complete.",
    sql: `SELECT TRUNC(bill_dt, 'MM') AS month,
       COUNT(*) AS bills_completed
FROM CI_BILL
WHERE bill_stat_flg = 'C'
  AND bill_dt >= ADD_MONTHS(TRUNC(SYSDATE, 'MM'), -12)
GROUP BY TRUNC(bill_dt, 'MM')
ORDER BY month`,
    chartDimension: "month",
    chartMeasure: "bills_completed",
    chartType: "line",
    sortTimeSeries: true,
  },
  {
    id: "odbt_payments_by_tender",
    category: "Payments",
    title: "Payments by tender type",
    description: "How customers paid, with dollar totals.",
    tip: "Columns are listed explicitly: SELECT * is blocked on CI_PAY_TNDR (protected columns).",
    sql: `SELECT t.tender_type_cd,
       COUNT(*) AS tenders,
       SUM(t.tender_amt) AS amount
FROM CI_PAY_TNDR t
GROUP BY t.tender_type_cd
ORDER BY amount DESC`,
    chartDimension: "tender_type_cd",
    chartMeasure: "amount",
    chartType: "horizontal",
    isCurrency: true,
  },
  {
    id: "odbt_recent_fts",
    category: "Finance",
    title: "Recent financial transactions",
    description: "The latest frozen FTs, newest first.",
    tip: "Unqualified names resolve to CISADM here.",
    sql: `SELECT ft_id, ft_type_flg, accounting_dt, cur_amt, tot_amt, sa_id
FROM CI_FT
WHERE freeze_sw = 'Y'
ORDER BY accounting_dt DESC
FETCH FIRST 100 ROWS ONLY`,
  },
];

const ORACLE_DBT_TIPS: string[] = [
  "You are querying CISADM in this client's own Oracle instance — the schema you know from CIS. Unqualified names resolve there.",
  "Protected columns (MICR_ID, WEB_PASSWD, ALERT_INFO) are blocked, and SELECT * on CI_PAY_TNDR needs an explicit column list.",
  "Use FETCH FIRST n ROWS ONLY (not LIMIT) and TRUNC/ADD_MONTHS for dates.",
  "Oracle treats '' as NULL — test empty codes with IS NULL, never = ''.",
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
