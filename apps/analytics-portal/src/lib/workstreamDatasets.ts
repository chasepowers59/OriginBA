import type { WorkstreamGroup } from "./types";

/**
 * Called DATA SETS deliberately: "domain" already means a Jaspersoft domain in this
 * product, and two meanings for one word in the same UI is how people end up talking
 * past each other.
 *
 * C2M is two systems plus an asset register, and utility people think in exactly those
 * terms: the C side (CCB — who the customer is, what they were billed, what they paid,
 * what they owe), the M side (MDM — meters, the usage they produce, and the field work
 * that keeps them reading), and the shared plumbing underneath both.
 *
 * The rail listed nine workstreams flat, so that shape was invisible to anyone who
 * didn't already know it.
 *
 * The split is derived from what each workstream's canvases actually read, not from the
 * names: billing, cashiering, customer_ops, debt and finance are ci_* (CCB); meter_ops
 * is d1_* with the w1_* asset tables (rpt_asset_location is pure W1); field_ops is d1_*
 * activities and exceptions; common is ci_* shared services.
 *
 * This groups the EXISTING workstream ids and renames nothing. The ids carry per-user
 * access grants, so they are not ours to reshuffle for presentation.
 */
export type WorkstreamDataset = {
  id: string;
  label: string;
  hint: string;
  workstreamIds: string[];
};

export const WORKSTREAM_DATASETS: WorkstreamDataset[] = [
  {
    id: "customer",
    label: "Customer & revenue",
    hint: "The C side — CCB: accounts, billing, money in, money owed",
    workstreamIds: ["customer_ops", "billing", "cashiering", "debt", "finance"],
  },
  {
    id: "metering",
    label: "Metering & usage",
    hint: "The M side — MDM: meters read, usage produced, field work that keeps them reading",
    workstreamIds: ["meter_ops", "field_ops"],
  },
  {
    id: "assets",
    label: "Asset operations",
    hint: "The device estate itself — W1 asset records and where they sit",
    workstreamIds: ["assets"],
  },
  {
    id: "shared",
    label: "Shared services",
    hint: "Batch, exceptions and the plumbing every side runs on",
    workstreamIds: ["common"],
  },
];

/**
 * Workstreams arranged into their domains, in the domain's declared order so the rail
 * reads the same every time. A workstream nobody has classified yet lands in the last
 * domain rather than disappearing — an unclassified workstream is a missing line here,
 * never a hidden report.
 */
export function groupByDataset(
  workstreams: WorkstreamGroup[],
): (WorkstreamDataset & { workstreams: WorkstreamGroup[] })[] {
  const known = new Set(WORKSTREAM_DATASETS.flatMap((d) => d.workstreamIds));
  const unclassified = workstreams.filter((w) => !known.has(w.id));

  return WORKSTREAM_DATASETS.map((domain, i) => {
    const mine = domain.workstreamIds
      .map((id) => workstreams.find((w) => w.id === id))
      .filter(Boolean) as WorkstreamGroup[];
    const isLast = i === WORKSTREAM_DATASETS.length - 1;
    return { ...domain, workstreams: isLast ? [...mine, ...unclassified] : mine };
  }).filter((domain) => domain.workstreams.length > 0);
}
