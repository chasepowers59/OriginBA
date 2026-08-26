/** Format currency for utility revenue / billing amounts */
export function formatCurrency(value: unknown): string {
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  return n.toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: n % 1 === 0 ? 0 : 2,
  });
}

export function formatPercent(value: number, digits = 1): string {
  if (!Number.isFinite(value)) return "—";
  return `${value.toFixed(digits)}%`;
}

/** IDs and natural keys should stay literal — never compact to 90.47M-style labels. */
export function isIdentifierColumn(columnId?: string): boolean {
  if (!columnId) return false;
  const upper = columnId.toUpperCase();
  // Two naming worlds: legacy Oracle snapshots (ACCT_ID, TENDER_TYPE_CD) and the
  // dbt canvases' Title Case ("Account ID", "Bill Cycle Code", "Meter Badge
  // Number"). An identifier rendered with thousand separators ("1,358,301,387")
  // is corrupted for copy/paste and lookups, so this guard must cover both.
  // "Count" columns are measures, not identifiers -- only " NUMBER" matches here.
  return (
    upper.endsWith("_ID") ||
    upper.endsWith(" ID") ||
    upper === "ID" ||
    upper.endsWith("_KEY") ||
    upper.includes("NATURAL_KEY") ||
    upper.endsWith("_NBR") ||
    upper.endsWith("_CD") ||
    upper.endsWith(" CODE") ||
    upper.endsWith(" NUMBER")
  );
}

/** Table / preview cells — compact only for measure columns. */
export function formatCellValue(
  value: unknown,
  options?: { columnId?: string; isMeasure?: boolean; asCurrency?: boolean },
): string {
  if (value == null || value === "") return "—";
  if (typeof value === "string" && value.match(/^\d{4}-\d{2}-\d{2}/)) {
    return formatDateTime(value);
  }
  if (options?.asCurrency) return formatCurrency(value);
  if (isIdentifierColumn(options?.columnId)) return String(value);
  const n = Number(value);
  if (!Number.isFinite(n) || !String(value).match(/^-?\d/)) return String(value);
  if (options?.isMeasure) return formatNumber(n);
  if (Number.isInteger(n)) return n.toLocaleString();
  return n.toLocaleString(undefined, { maximumFractionDigits: 6 });
}

/** Format numbers for charts and KPIs */
export function formatNumber(value: unknown): string {
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  if (Math.abs(n) >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (Math.abs(n) >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  if (Number.isInteger(n)) return n.toLocaleString();
  return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

/** Full-precision values for chart hover tooltips (no K/M compaction). */
export function formatTooltipNumber(value: unknown): string {
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  if (Number.isInteger(n)) return n.toLocaleString();
  return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

export function formatTooltipCurrency(value: unknown): string {
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  return n.toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: n % 1 === 0 ? 0 : 2,
  });
}

export function formatDateTime(value: unknown): string {
  if (!value) return "—";
  const d = new Date(String(value));
  if (Number.isNaN(d.getTime())) return String(value);
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

export function workstreamLabel(key: string): string {
  // Re-export path kept for compatibility; prefer businessLabels.workstreamDisplayName
  return key.replace(/_/g, " ").replace(/\b\w/g, (c) => c.toUpperCase());
}

export function defaultDateRangeYtd(): [string, string] {
  const end = new Date();
  const start = new Date(end.getFullYear(), 0, 1);
  return [start.toISOString().slice(0, 10), end.toISOString().slice(0, 10)];
}

export function defaultDateRangeLastMonth(): [string, string] {
  const end = new Date();
  end.setDate(0); // last day of previous month
  const start = new Date(end.getFullYear(), end.getMonth(), 1);
  return [start.toISOString().slice(0, 10), end.toISOString().slice(0, 10)];
}

export function exportRowsCsv(columns: string[], rows: Record<string, unknown>[], filename: string) {
  const escape = (v: unknown) => {
    const s = String(v ?? "");
    return s.includes(",") || s.includes('"') ? `"${s.replace(/"/g, '""')}"` : s;
  };
  const lines = [columns.join(",")];
  for (const row of rows) {
    lines.push(columns.map((c) => escape(row[c])).join(","));
  }
  const blob = new Blob([lines.join("\n")], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const a = document.createElement("a");
  a.href = url;
  a.download = filename;
  a.click();
  URL.revokeObjectURL(url);
}
