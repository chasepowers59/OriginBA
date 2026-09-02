import type { SnapshotMetadata } from "./types";

/**
 * Fallback names and display order for the workstreams, used when the API has not
 * supplied a label. It must carry the UNION of both deployment shapes: the dbt catalog
 * has `assets` and no `new_services`, the legacy CISADM catalog has `new_services` and
 * no `assets`, so neither id is dead -- each is real in one shape. This list was a copy
 * of the legacy nine and never gained `assets`, which made /workstream/assets a 404.
 * businessLabels.test.ts pins it against the catalog files so it cannot drift again.
 */
export const WORKSTREAM_ORDER = [
  "finance",
  "billing",
  "meter_ops",
  "cashiering",
  "debt",
  "customer_ops",
  "new_services",
  "assets",
  "field_ops",
  "common",
] as const;

export const WORKSTREAM_LABELS: Record<string, string> = {
  billing: "Billing & Rates",
  finance: "Finance",
  customer_ops: "Customer Operations",
  meter_ops: "Meter Operations",
  common: "Operations & Shared Services",
  field_ops: "Field Operations",
  debt: "Collections & Debt",
  cashiering: "Cashiering & Payments",
  new_services: "New Services",
  assets: "Asset Operations",
};

export const WORKSTREAM_DESCRIPTIONS: Record<string, string> = {
  billing: "Bill segments, determinant usage, cycles, and rate performance",
  finance: "Transactions, GL distribution, billable charges, and revenue",
  // Device assets moved out to their own workstream when assets became a data set;
  // leaving them named here sent people to the wrong workstream for them.
  meter_ops: "Usage, measurements, and scalar detail",
  cashiering: "Payments, tenders, and cashiering activity",
  debt: "Aged balances, collections, and write-off processes",
  customer_ops: "Accounts, customers, cases, and service locations",
  new_services: "New services pipeline and start-service tracking",
  assets: "Meter and device assets, and the locations they serve",
  field_ops: "Field activities, crews, and BODA field work",
  common: "Workflow queues, batch jobs, and cross-cutting exceptions",
};

export const FIELD_ROLE_LABELS: Record<string, string> = {
  dimension: "Field",
  measure: "Measure",
  date: "Date",
};

export function fieldRoleLabel(role: string): string {
  return FIELD_ROLE_LABELS[role] ?? role.replace(/_/g, " ");
}

export const AGGREGATION_LABELS: Record<string, string> = {
  count: "Count of records",
  count_distinct: "Distinct count",
  sum: "Total",
  min: "Minimum",
  max: "Maximum",
};

export const SNAPSHOT_BUSINESS: Record<
  string,
  { headline?: string; summary: string; grainDescription: string; dateLabel: string }
> = {
  WORKFLOW_QUEUE_RPT_CURR: {
    summary:
      "Monitor staff to-dos, assignments, aging, and overnight batch runs from a single operational dashboard.",
    grainDescription: "One row per to-do item or batch processing thread",
    dateLabel: "To-do created date",
  },
  BSEG_BILLED_USAGE_RPT_CURR: {
    summary:
      "Analyze billed charges on completed bills — by customer class, cycle, rate, and service type.",
    grainDescription: "One row per completed bill segment",
    dateLabel: "Bill date",
  },
  FT_RPT_CURR: {
    summary:
      "Track financial transaction volume, revenue mix, adjustments, and GL distribution status.",
    grainDescription: "One row per financial transaction (non-redundant)",
    dateLabel: "Accounting date",
  },
  CASE_PREM_CONTACT_RPT_CURR: {
    summary:
      "Understand customer case workload by type, status, division, and service location.",
    grainDescription: "One row per customer case",
    dateLabel: "Case opened date",
  },
  OPS_EXCEPTION_RPT_CURR: {
    summary:
      "Prioritize billing, usage, and validation exceptions — open workload by source and severity.",
    grainDescription: "One row per operational exception",
    dateLabel: "Exception created date",
  },
};

export function workstreamDisplayName(key: string): string {
  return WORKSTREAM_LABELS[key] ?? key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function aggregationLabel(agg: string): string {
  return AGGREGATION_LABELS[agg.toLowerCase()] ?? agg;
}

export function snapshotSummary(meta: Pick<SnapshotMetadata, "id" | "summary">): string {
  return meta.summary ?? SNAPSHOT_BUSINESS[meta.id]?.summary ?? "";
}

export function snapshotGrainDescription(
  meta: Pick<SnapshotMetadata, "id" | "grain_description" | "grain">,
): string {
  return meta.grain_description ?? SNAPSHOT_BUSINESS[meta.id]?.grainDescription ?? meta.grain;
}

export function requiredDateLabel(meta: SnapshotMetadata): string {
  if (meta.required_date_label) return meta.required_date_label;
  const field = meta.date_fields.find((d) => d.id === meta.required_date_field);
  if (field?.label) return field.label;
  return SNAPSHOT_BUSINESS[meta.id]?.dateLabel ?? "Reporting period";
}

/** Build friendly table/chart column headers from metadata + query shape */
export function buildColumnLabels(
  meta: SnapshotMetadata,
  dimensionIds: string[],
  measureField: string,
  measureAgg: string,
  resultColumns: string[],
): Record<string, string> {
  const labels: Record<string, string> = {};
  const dimMap = Object.fromEntries(meta.dimensions.map((d) => [d.id, d.label]));
  const measureMap = Object.fromEntries(meta.measures.map((m) => [m.id, m.label]));

  dimensionIds.forEach((id, idx) => {
    const col = resultColumns[idx];
    if (col) labels[col] = dimMap[id] ?? prettifyFieldName(id);
  });

  const measureCol = resultColumns[resultColumns.length - 1];
  if (measureCol) {
    labels[measureCol] = measureColumnLabel(
      measureField,
      measureAgg,
      measureMap[measureField],
    );
  }

  return labels;
}

/** Kept upper when a word is one of these; everything else gets Title Case. */
const ACRONYMS = new Set([
  "ID", "SA", "SP", "GL", "FT", "BS", "BX", "MC", "SQ", "UOM", "TOU", "AMI", "CIS",
  "PO", "AR", "QA", "US",
]);

function capitalize(word: string): string {
  // Split on "/" so a suffix expansion like "date/time" reads "Date/Time".
  return word
    .split("/")
    .map((part) =>
      ACRONYMS.has(part.toUpperCase())
        ? part.toUpperCase()
        : part.charAt(0).toUpperCase() + part.slice(1).toLowerCase(),
    )
    .join("/");
}

/**
 * A column identifier as a human would write it.
 *
 * This must be safe on BOTH deployment shapes, because it is called on ids from either:
 * a dbt canvas field is already a business name ("Bill Date"), a legacy snapshot's is a
 * database column ("ACCOUNTING_DT"), and the SQL workspace passes raw Postgres columns
 * ("bill_id"). The previous version only upper-cased each word's FIRST letter and never
 * lowered the rest, so the all-caps legacy form — the one it was written for — came out
 * shouting: "ACCOUNTING Date", "CUSTOMER CLASS". That is six of the nine orgs, on every
 * surface that calls this.
 *
 * A name that already contains a SPACE was authored for people and is returned
 * untouched. That is what protects "Service Agreement ID" from being lowered to
 * "Service Agreement Id" — the reason a blanket toLowerCase is wrong here.
 */
export function prettifyFieldName(fieldId: string): string {
  if (/\s/.test(fieldId)) return fieldId;
  return fieldId
    .replace(/^FK_/i, "")
    .replace(/_DESC$/i, "")
    // Absorb a STATUS/STAT stem into the one expanded word: 22 legacy ids end
    // _STATUS_FLG or _STAT_FLG (BILL_STAT_FLG, SA_STATUS_FLG, PAY_STATUS_FLG among
    // them) and appending to those produced "Adj Status Status".
    .replace(/(?:_(?:STATUS|STAT))?_FLG$/i, "_status")
    .replace(/_CD$/i, "")
    .replace(/_DTTM$/i, "_date/time")
    .replace(/_DT$/i, "_date")
    .replace(/_AMT$/i, "_amount")
    .replace(/_NBR$/i, "_number")
    .replace(/_ID$/i, "")
    .split("_")
    .filter(Boolean)
    .map(capitalize)
    .join(" ")
    .trim();
}

export function measureIsCurrency(fieldId: string): boolean {
  const upper = fieldId.toUpperCase();
  return upper.includes("AMT") || upper.includes("DEBT") || upper.includes("REVENUE");
}

/** Dollar formatting only for sum/min/max on amount-like fields — never for counts. */
export function measureDisplaysAsCurrency(measureField: string, measureAgg: string): boolean {
  if (measureField === "*") return false;
  if (measureAgg === "count" || measureAgg === "count_distinct") return false;
  return measureIsCurrency(measureField);
}

export function defaultMeasureSelection(
  meta: Pick<SnapshotMetadata, "measures" | "trusted_measures">,
): { field: string; agg: string } {
  const trusted = meta.trusted_measures ?? [];
  const preferred = meta.measures.find((m) => trusted.includes(m.id));
  if (preferred) {
    return { field: preferred.id, agg: preferred.aggs[0] ?? "sum" };
  }
  const records = meta.measures.find((m) => m.id === "*");
  return { field: "*", agg: records?.aggs[0] ?? "count" };
}

export function allowedAggsForMeasure(
  meta: Pick<SnapshotMetadata, "measures">,
  measureField: string,
): string[] {
  return meta.measures.find((m) => m.id === measureField)?.aggs ?? ["count"];
}

export function measureColumnLabel(
  measureField: string,
  measureAgg: string,
  measureLabel?: string,
): string {
  if (measureField === "*") {
    return measureAgg === "count" ? "Number of records" : aggregationLabel(measureAgg);
  }
  const base = measureLabel ?? prettifyFieldName(measureField);
  if (measureAgg === "sum" && measureIsCurrency(measureField)) {
    return `Total ${base.toLowerCase()}`;
  }
  if (measureAgg === "sum") {
    return `Total ${base.toLowerCase()}`;
  }
  if (measureAgg === "count") {
    return `Rows with ${base.toLowerCase()}`;
  }
  if (measureAgg === "count_distinct") {
    return `Distinct ${base.toLowerCase()}`;
  }
  return `${aggregationLabel(measureAgg)} — ${base}`;
}

export function kpiLabelsForMeasure(measureField: string, measureAgg: string) {
  const groups = "Categories";
  if (measureField === "*") {
    return {
      total: "Total records",
      groups,
      breakdown: "Breakdown by",
    };
  }
  if (measureDisplaysAsCurrency(measureField, measureAgg)) {
    return {
      total: measureAgg === "sum" ? "Total amount" : aggregationLabel(measureAgg),
      groups,
      breakdown: "Breakdown by",
    };
  }
  if (measureAgg === "count" || measureAgg === "count_distinct") {
    return {
      total: measureAgg === "count_distinct" ? "Distinct count" : "Non-null count",
      groups,
      breakdown: "Breakdown by",
    };
  }
  if (measureField.includes("SQ") || measureField.includes("USAGE")) {
    return {
      total: measureAgg === "sum" ? "Total usage" : aggregationLabel(measureAgg),
      groups,
      breakdown: "Breakdown by",
    };
  }
  return {
    total: measureAgg === "sum" ? "Combined total" : aggregationLabel(measureAgg),
    groups,
    breakdown: "Breakdown by",
  };
}
