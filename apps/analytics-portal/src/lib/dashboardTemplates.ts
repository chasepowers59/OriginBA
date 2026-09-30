import type { DashboardTileDef } from "@/lib/types";

export type DashboardTemplate = {
  id: string;
  workstream: string;
  title: string;
  description: string;
  days: number;
  tiles: Omit<DashboardTileDef, "id">[];
};

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

export const ALL_DASHBOARD_TEMPLATES: DashboardTemplate[] = WAREHOUSE_DASHBOARD_TEMPLATES;

/** Templates whose every tile can run on this org's catalog. */
export function templatesForSnapshots(availableIds: Set<string>): DashboardTemplate[] {
  return ALL_DASHBOARD_TEMPLATES.filter((t) =>
    t.tiles.every((tile) => availableIds.has(tile.snapshot_id)),
  );
}
