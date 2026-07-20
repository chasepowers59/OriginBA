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
