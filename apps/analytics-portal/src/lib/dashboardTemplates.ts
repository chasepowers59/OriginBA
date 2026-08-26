import type { DashboardTileDef } from "@/lib/types";

export type DashboardTemplate = {
  id: string;
  workstream: string;
  title: string;
  description: string;
  days: number;
  tiles: Omit<DashboardTileDef, "id">[];
};

export const DASHBOARD_TEMPLATES: DashboardTemplate[] = [
  {
    id: "billing_ops",
    workstream: "billing",
    title: "Billing operations",
    description: "Revenue, usage, and billing backlog at a glance.",
    days: 90,
    tiles: [
      {
        slot: 0,
        title: "Billed revenue",
        visual: "kpi",
        snapshot_id: "BSEG_BILLED_USAGE_RPT_CURR",
        report_id: "amount_by_class",
        chart_type: "bar",
      },
      {
        slot: 1,
        title: "Usage by UOM",
        visual: "chart",
        snapshot_id: "BSEG_SQ_USAGE_RPT_CURR",
        report_id: "volume_by_dimension",
        chart_type: "bar",
      },
      {
        slot: 2,
        title: "Billing todos",
        visual: "chart",
        snapshot_id: "WORKFLOW_QUEUE_RPT_CURR",
        report_id: "todo_by_status",
        chart_type: "bar",
      },
      {
        slot: 3,
        title: "Open exceptions",
        visual: "chart",
        snapshot_id: "OPS_EXCEPTION_RPT_CURR",
        report_id: "excp_open",
        chart_type: "bar",
      },
    ],
  },
  {
    id: "finance",
    workstream: "finance",
    title: "Finance overview",
    description: "Transactions and billable charges.",
    days: 180,
    tiles: [
      {
        slot: 0,
        title: "Transaction dollars",
        visual: "kpi",
        snapshot_id: "FT_RPT_CURR",
        report_id: "ft_by_type",
        chart_type: "bar",
      },
      {
        slot: 1,
        title: "By transaction type",
        visual: "chart",
        snapshot_id: "FT_RPT_CURR",
        report_id: "ft_by_type",
        chart_type: "bar",
      },
      {
        slot: 2,
        title: "GL posting status",
        visual: "chart",
        snapshot_id: "FT_RPT_CURR",
        report_id: "ft_gl_status",
        chart_type: "pie",
      },
      {
        slot: 3,
        title: "Billable charges",
        visual: "chart",
        snapshot_id: "BILLABLE_CHARGE_RPT_CURR",
        report_id: "volume_by_dimension",
        chart_type: "bar",
      },
    ],
  },
  {
    id: "cashiering",
    workstream: "cashiering",
    title: "Payments & cashiering",
    description: "Payment volume and tender mix.",
    days: 90,
    tiles: [
      {
        slot: 0,
        title: "Payment dollars",
        visual: "kpi",
        snapshot_id: "PAY_EVENT_RPT_CURR",
        report_id: "payments_by_method",
        chart_type: "bar",
      },
      {
        slot: 1,
        title: "By tender type",
        visual: "chart",
        snapshot_id: "PAY_EVENT_RPT_CURR",
        report_id: "payments_by_method",
        chart_type: "bar",
      },
      {
        slot: 2,
        title: "By status",
        visual: "chart",
        snapshot_id: "PAY_EVENT_RPT_CURR",
        report_id: "payments_by_status",
        chart_type: "pie",
      },
      { slot: 3, title: "Reserve", visual: "kpi", snapshot_id: "PAY_EVENT_RPT_CURR", chart_type: "bar" },
    ],
  },
  {
    id: "customer_ops",
    workstream: "customer_ops",
    title: "Customer operations",
    description: "Accounts, cases, and service locations.",
    days: 180,
    tiles: [
      {
        slot: 0,
        title: "Accounts",
        visual: "kpi",
        snapshot_id: "ACCT_CUSTOMER_RPT_CURR",
        report_id: "volume_by_dimension",
        chart_type: "bar",
      },
      {
        slot: 1,
        title: "Cases by type",
        visual: "chart",
        snapshot_id: "CASE_PREM_CONTACT_RPT_CURR",
        report_id: "cases_by_type",
        chart_type: "bar",
      },
      {
        slot: 2,
        title: "By customer class",
        visual: "chart",
        snapshot_id: "ACCT_CUSTOMER_RPT_CURR",
        report_id: "volume_by_dimension",
        chart_type: "bar",
      },
      { slot: 3, title: "Reserve", visual: "kpi", snapshot_id: "CASE_PREM_CONTACT_RPT_CURR", chart_type: "bar" },
    ],
  },
  {
    id: "operations",
    workstream: "common",
    title: "Operations control tower",
    description: "Exceptions, workflow, and batch health.",
    days: 30,
    tiles: [
      {
        slot: 0,
        title: "Open exceptions",
        visual: "kpi",
        snapshot_id: "OPS_EXCEPTION_RPT_CURR",
        report_id: "excp_open",
        chart_type: "bar",
      },
      {
        slot: 1,
        title: "By severity",
        visual: "chart",
        snapshot_id: "OPS_EXCEPTION_RPT_CURR",
        report_id: "excp_open",
        chart_type: "bar",
      },
      {
        slot: 2,
        title: "Open todos",
        visual: "chart",
        snapshot_id: "WORKFLOW_QUEUE_RPT_CURR",
        report_id: "todo_by_status",
        chart_type: "bar",
      },
      {
        slot: 3,
        title: "Batch jobs",
        visual: "chart",
        snapshot_id: "WORKFLOW_QUEUE_RPT_CURR",
        report_id: "batch_by_status",
        chart_type: "bar",
      },
    ],
  },
];

export function templatesForWorkstream(workstream: string): DashboardTemplate[] {
  return DASHBOARD_TEMPLATES.filter((t) => t.workstream === workstream);
}

// ---------------------------------------------------------------------------
// WAREHOUSE templates — tiles on the dbt reporting canvases. Every dimension,
// measure, and date field verified against output/catalog_dbt.json; the page
// offers a template only when the org's catalog carries all of its snapshots.
// ---------------------------------------------------------------------------

export const WAREHOUSE_DASHBOARD_TEMPLATES: DashboardTemplate[] = [
  {
    id: "wh_billing_ops",
    workstream: "billing",
    title: "Billing operations",
    description: "Billed revenue, trend, and the charge lines behind it.",
    days: 180,
    tiles: [
      {
        slot: 0,
        title: "Billed revenue by customer class",
        visual: "chart",
        snapshot_id: "rpt_bill_segment",
        dimensions: ["Customer Class"],
        measure_field: "Billed Amount",
        measure_agg: "sum",
        chart_type: "bar",
      },
      {
        slot: 1,
        title: "Billed revenue by month",
        visual: "chart",
        snapshot_id: "rpt_bill_segment",
        measure_field: "Billed Amount",
        measure_agg: "sum",
        chart_type: "line",
        time_grain: "month",
      },
      {
        slot: 2,
        title: "Top charge descriptions",
        visual: "chart",
        snapshot_id: "rpt_billed_charge",
        dimensions: ["Charge Description"],
        measure_field: "Billed Amount",
        measure_agg: "sum",
        chart_type: "bar",
      },
      {
        slot: 3,
        title: "Bill segments by SA type",
        visual: "chart",
        snapshot_id: "rpt_bill_segment",
        dimensions: ["SA Type"],
        chart_type: "bar",
      },
    ],
  },
  {
    id: "wh_payments_collections",
    workstream: "cashiering",
    title: "Payments & collections",
    description: "Tenders, payment trend, and financial transaction mix.",
    days: 180,
    tiles: [
      {
        slot: 0,
        title: "Tendered dollars by tender type",
        visual: "chart",
        snapshot_id: "rpt_payment_tender",
        dimensions: ["Tender Type"],
        measure_field: "Tender Amount",
        measure_agg: "sum",
        chart_type: "bar",
      },
      {
        slot: 1,
        title: "Payments by month",
        visual: "chart",
        snapshot_id: "rpt_payment_tender",
        measure_field: "Tender Amount",
        measure_agg: "sum",
        chart_type: "line",
        time_grain: "month",
      },
      {
        slot: 2,
        title: "FT dollars by transaction type",
        visual: "chart",
        snapshot_id: "rpt_financial_txn",
        dimensions: ["FT Type"],
        measure_field: "Current Amount",
        measure_agg: "sum",
        chart_type: "bar",
      },
      {
        slot: 3,
        title: "Payments by customer class",
        visual: "chart",
        snapshot_id: "rpt_payment_tender",
        dimensions: ["Customer Class"],
        measure_field: "Tender Amount",
        measure_agg: "sum",
        chart_type: "bar",
      },
    ],
  },
  {
    id: "wh_meter_ops",
    workstream: "meter_ops",
    title: "Meter operations",
    description: "Measurement volume and the device fleet behind it.",
    days: 180,
    tiles: [
      {
        slot: 0,
        title: "Measurements by month",
        visual: "chart",
        snapshot_id: "rpt_measurement",
        chart_type: "line",
        time_grain: "month",
      },
      {
        slot: 1,
        title: "Measured volume by device type",
        visual: "chart",
        snapshot_id: "rpt_measurement",
        dimensions: ["Device Type"],
        measure_field: "Measurement Value",
        measure_agg: "sum",
        chart_type: "bar",
      },
      {
        slot: 2,
        title: "Open To Dos by type",
        visual: "chart",
        snapshot_id: "rpt_todo",
        dimensions: ["To Do Type"],
        chart_type: "bar",
      },
      {
        slot: 3,
        title: "Devices by type",
        visual: "chart",
        snapshot_id: "rpt_device_asset",
        dimensions: ["Device Type"],
        chart_type: "bar",
      },
    ],
  },
  {
    id: "wh_customer_ops",
    workstream: "customer_ops",
    title: "Customer operations",
    description: "The service agreement portfolio at a glance.",
    days: 365,
    tiles: [
      {
        slot: 0,
        title: "Service agreements by type",
        visual: "chart",
        snapshot_id: "rpt_service_agreement",
        dimensions: ["SA Type"],
        chart_type: "bar",
      },
      {
        slot: 1,
        title: "Service agreements by status",
        visual: "chart",
        snapshot_id: "rpt_service_agreement",
        dimensions: ["SA Status"],
        chart_type: "bar",
      },
      {
        slot: 2,
        title: "New SAs by month",
        visual: "chart",
        snapshot_id: "rpt_service_agreement",
        chart_type: "line",
        time_grain: "month",
      },
      {
        slot: 3,
        title: "Current balance by customer class",
        visual: "chart",
        snapshot_id: "rpt_service_agreement",
        dimensions: ["Customer Class"],
        measure_field: "Current Balance",
        measure_agg: "sum",
        chart_type: "bar",
      },
    ],
  },
];

export const ALL_DASHBOARD_TEMPLATES: DashboardTemplate[] = [
  ...WAREHOUSE_DASHBOARD_TEMPLATES,
  ...DASHBOARD_TEMPLATES,
];

/** Templates whose every tile can run on this org's catalog. */
export function templatesForSnapshots(availableIds: Set<string>): DashboardTemplate[] {
  return ALL_DASHBOARD_TEMPLATES.filter((t) =>
    t.tiles.every((tile) => availableIds.has(tile.snapshot_id)),
  );
}
