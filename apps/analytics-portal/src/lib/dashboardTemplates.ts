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
