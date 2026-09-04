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
  "Add a date filter (last 6 months) to keep queries fast on large tables like CI_FT and CI_BSEG.",
  "The reporting canvases (rpt_*) are queryable here too, beside CISADM — the governed, already-joined view of the same data.",
  "Press Ctrl+Enter (⌘+Enter on Mac) to run the statement.",
  "Toggle Chart view when your result has categories and numbers — great for monthly trends or class breakdowns.",
  "Row count runs a full COUNT(*) and can be slow on big tables — use it when you really need the total.",
];

export const DATABASE_QUERY_TEMPLATES: DatabaseQueryTemplate[] = [
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
