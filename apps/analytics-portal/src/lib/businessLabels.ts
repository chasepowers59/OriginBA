import type { SnapshotMetadata } from "./types";

/**
 * Fallback names and display order for the workstreams, used when the API has not
 * supplied a label. There is ONE catalog and this is its `workstream_order`, verbatim;
 * businessLabels.test.ts pins the two against each other so a hand-kept copy cannot
 * drift -- the last drift left /workstream/assets a 404 while the catalog carried it.
 */
export const WORKSTREAM_ORDER = [
  "billing",
  "finance",
  "cashiering",
  "debt",
  "customer_ops",
  "meter_ops",
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

export function workstreamDisplayName(key: string): string {
  return WORKSTREAM_LABELS[key] ?? key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function aggregationLabel(agg: string): string {
  return AGGREGATION_LABELS[agg.toLowerCase()] ?? agg;
}

export function snapshotSummary(meta: Pick<SnapshotMetadata, "summary">): string {
  return meta.summary ?? "";
}

export function snapshotGrainDescription(
  meta: Pick<SnapshotMetadata, "grain_description" | "grain">,
): string {
  return meta.grain_description ?? meta.grain;
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
 * This must be safe on BOTH forms an id arrives in: a canvas field is already a
 * business name ("Bill Date"), while the SQL workspace passes raw CISADM columns
 * ("ACCOUNTING_DT") and raw Postgres columns ("bill_id"). The previous version only
 * upper-cased each word's FIRST letter and never lowered the rest, so the all-caps form
 * — the one it was written for — came out shouting: "ACCOUNTING Date", "CUSTOMER CLASS".
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
    // Absorb a STATUS/STAT stem into the one expanded word: 22 CISADM column ids end
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

/** Whole words that mean money. Matched as TOKENS, never as substrings — see below. */
const CURRENCY_WORDS = new Set([
  "AMT", "AMOUNT", "AMOUNTS", "BALANCE", "REVENUE", "DEBT", "ARREARS",
  "PRICE", "COST", "FEE", "FEES",
]);

/** Words that mean this is a tally or a ratio, whatever money word sits beside it. */
const NOT_CURRENCY_WORDS = new Set(["COUNT", "COUNTS", "PERCENT", "PCT", "RATE", "RATIO"]);

/**
 * Whether a measure holds money, in EITHER naming world.
 *
 * This was `includes("AMT") || includes("DEBT") || includes("REVENUE")` -- written for
 * CISADM's `_AMT` suffix, and "AMOUNT" does not contain "AMT" (A-M-O-U-N-T). Measured:
 * of 47 money-ish measures in catalog_dbt, exactly ONE was detected, so nearly every
 * money column on the 38 canvases rendered as a bare number. CISADM-style names such as
 * GL_AMOUNT miss for the same reason.
 *
 * Matching TOKENS rather than substrings is the actual fix; widening the substring list
 * just reproduces the bug pointing the other way. Three false positives that a wider
 * substring rule would have introduced, each found by reading what it newly matched:
 * "Days Unbalanced" (UNBALANCED contains BALANCE, and it counts days), "% of Arrears
 * Collected", and GOVERNED_ARREARS_FT_COUNT. Splitting on non-alphanumerics is what
 * makes BILL_AMT work where a \b regex would not -- underscore is a word character.
 *
 * The negative set is specific on purpose: "Arrears 0-30 Days" IS currency, so
 * excluding on "Days" would have been the lazy version of the same mistake.
 */
export function measureIsCurrency(fieldId: string): boolean {
  if (fieldId.includes("%")) return false;
  const words = fieldId.toUpperCase().split(/[^A-Z0-9]+/).filter(Boolean);
  if (words.some((w) => NOT_CURRENCY_WORDS.has(w))) return false;
  return words.some((w) => CURRENCY_WORDS.has(w));
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
