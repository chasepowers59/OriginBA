/** Format currency for utility revenue / billing amounts */
export function formatCurrency(value: unknown): string {
  // A missing value is NOT zero: Number(null) and Number("") are both 0, so a NULL
  // amount rendered as a real "$0" while undefined rendered "—". A SUM over zero
  // matching rows IS null, and the backend distinguishes that state deliberately
  // (kpi_runner.empty_window_note), so erasing it here turns "no data" into a business
  // fact the reader will act on. formatCellValue already guarded this way.
  if (value == null || value === "") return "—";
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

/** Whole words naming an identifier, matched as TOKENS rather than suffixes. */
const IDENTIFIER_WORDS = new Set(["ID", "IDS", "KEY", "KEYS", "PATH", "GUID", "UUID"]);

/** Words meaning this is a tally or a state, whatever identifier word sits beside it. */
const NOT_IDENTIFIER_WORDS = new Set([
  "COUNT", "COUNTS", "REQUIRED", "FLAG", "TOTAL", "AMOUNT", "PERCENT", "PCT",
]);

/** IDs and natural keys should stay literal — never compact to 90.47M-style labels. */
export function isIdentifierColumn(columnId?: string): boolean {
  if (!columnId) return false;
  const upper = columnId.toUpperCase();
  // Suffixes alone missed names whose shape is not a suffix. Found by running REAL
  // Ellensburg values through this: "Hierarchy Path" rendered '498295347400' as
  // "498,295,347,400" and "Drill Key Values" did the same -- both round-trip, so the
  // round-trip guard in formatCellValue cannot see them either. Token matching also
  // catches "Adjustment ID (Pay Seg)", which endsWith(" ID") missed over a
  // parenthetical. The negative set keeps "Drill Key Count" (a measure that wants its
  // separators) and "Key Required" (a flag) out.
  const words = upper.split(/[^A-Z0-9]+/).filter(Boolean);
  if (!words.some((w) => NOT_IDENTIFIER_WORDS.has(w))
      && words.some((w) => IDENTIFIER_WORDS.has(w))) {
    return true;
  }
  // Two naming worlds: raw CISADM columns from the SQL workspace (ACCT_ID,
  // TENDER_TYPE_CD) and the canvases' Title Case ("Account ID", "Bill Cycle Code",
  // "Meter Badge Number"). An identifier rendered with thousand separators
  // ("1,358,301,387") is corrupted for copy/paste and lookups, so this guard must
  // cover both.
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

/**
 * Render a flag column as a state, never a raw 1/0 or bare true/false.
 *
 * A flag reaches the UI in several encodings depending on the backend: a genuine
 * boolean on the Postgres/Supabase path, a NUMBER(1) 1/0 on the Oracle path, or a
 * Y/N/T/F string. All of them mean the same thing on a BI surface, so normalise to
 * one readable pair. Undecidable values fall through to their string form.
 */
export function formatBoolean(value: unknown): string {
  if (value == null || value === "") return "—";
  if (typeof value === "boolean") return value ? "True" : "False";
  const s = String(value).trim().toLowerCase();
  if (["1", "t", "true", "y", "yes"].includes(s)) return "True";
  if (["0", "f", "false", "n", "no"].includes(s)) return "False";
  return String(value);
}

/** Table / preview cells — compact only for measure columns. */
export function formatCellValue(
  value: unknown,
  options?: { columnId?: string; isMeasure?: boolean; asCurrency?: boolean; isBoolean?: boolean },
): string {
  if (value == null || value === "") return "—";
  // Flags render as a state. A native JS boolean is always a flag (Postgres path);
  // a NUMBER(1) 1/0 flag is indistinguishable from an integer by value alone, so the
  // caller declares it via isBoolean from the column's declared type (Oracle path).
  if (options?.isBoolean || typeof value === "boolean") return formatBoolean(value);
  if (typeof value === "string" && value.match(/^\d{4}-\d{2}-\d{2}/)) {
    return formatDateTime(value);
  }
  if (options?.asCurrency) return formatCurrency(value);
  if (isIdentifierColumn(options?.columnId)) return String(value);
  const n = Number(value);
  if (!Number.isFinite(n) || !String(value).match(/^-?\d/)) return String(value);
  // A STRING is only rendered as a number when doing so LOSES NOTHING. The name-based
  // guard above cannot cover this: measured across all 958 text columns in
  // originba_v2_demo25, eight hold leading-zero digit strings under names that share no
  // suffix -- rpt_gl."GL Account", rpt_characteristics."Ad Hoc Value",
  // rpt_asset_location."Hierarchy Path", rpt_todo."Drill Key Values" among them. The
  // worst rendered '01000123923000000000000' as "1,000,123,923,000,000,000,000": the
  // key field of a FINANCE canvas, past 2^53, so the leading zero AND the trailing
  // digits were wrong. Lossless is: a plain decimal, no leading zero, integer part
  // within 2^53 -- formatted at ITS OWN scale, because the API serializes NUMERIC
  // columns at the column scale and a strict String(n) round-trip left "-1265.00" raw
  // beside a formatted "-1,561.11" in the same row.
  if (typeof value === "string") {
    const m = value.trim().match(/^-?(0|[1-9]\d*)(?:\.(\d+))?$/);
    if (!m || !Number.isSafeInteger(Math.trunc(n))) return value;
    if (options?.isMeasure) return formatNumber(n);
    const scale = Math.min(m[2]?.length ?? 0, 6);
    return n.toLocaleString(undefined, { minimumFractionDigits: scale, maximumFractionDigits: scale });
  }
  if (options?.isMeasure) return formatNumber(n);
  if (Number.isInteger(n)) return n.toLocaleString();
  return n.toLocaleString(undefined, { maximumFractionDigits: 6 });
}

/** Format numbers for charts and KPIs */
export function formatNumber(value: unknown): string {
  if (value == null || value === "") return "—";
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  if (Math.abs(n) >= 1_000_000) return `${(n / 1_000_000).toFixed(2)}M`;
  if (Math.abs(n) >= 1_000) return `${(n / 1_000).toFixed(1)}K`;
  if (Number.isInteger(n)) return n.toLocaleString();
  return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

/** Full-precision values for chart hover tooltips (no K/M compaction). */
export function formatTooltipNumber(value: unknown): string {
  if (value == null || value === "") return "—";
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  if (Number.isInteger(n)) return n.toLocaleString();
  return n.toLocaleString(undefined, { maximumFractionDigits: 2 });
}

export function formatTooltipCurrency(value: unknown): string {
  if (value == null || value === "") return "—";
  const n = Number(value);
  if (!Number.isFinite(n)) return "—";
  return n.toLocaleString(undefined, {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: n % 1 === 0 ? 0 : 2,
  });
}

/** YYYY-MM-DD with nothing after it: a calendar date, not an instant. */
const DATE_ONLY_RE = /^\d{4}-\d{2}-\d{2}$/;

/**
 * A timestamp in the viewer's clock, or a plain date left on its own calendar day.
 *
 * `new Date("2026-09-02")` is specified to parse as UTC MIDNIGHT, while
 * `new Date("2026-09-02T00:00:00")` parses as local midnight. Feeding the first form to
 * toLocaleString rendered every date-only value as THE PREVIOUS DAY west of UTC, with a
 * time nobody supplied: "2026-09-02" came out "Sep 1, 2026, 06:00 PM". The API
 * serializes a Postgres DATE column with `date.isoformat()`, which is exactly that
 * form, so a bill dated the 1st displayed the 31st on every canvas that has one.
 *
 * Found by running real Ellensburg values through this function. Bug class 12 a third
 * time, after report_schedules and the date-range builders: a business date belongs in
 * the utility's own calendar, never as a UTC instant. A date with no time is also
 * rendered WITHOUT one, rather than inventing midnight-shifted-into-evening.
 */
export function formatDateTime(value: unknown): string {
  if (!value) return "—";
  const raw = String(value);
  if (DATE_ONLY_RE.test(raw)) {
    const [y, m, d] = raw.split("-").map(Number);
    const local = new Date(y, m - 1, d);          // local midnight, so the day survives
    if (Number.isNaN(local.getTime())) return raw;
    return local.toLocaleDateString(undefined, {
      month: "short",
      day: "numeric",
      year: "numeric",
    });
  }
  const d = new Date(raw);
  if (Number.isNaN(d.getTime())) return raw;
  return d.toLocaleString(undefined, {
    month: "short",
    day: "numeric",
    year: "numeric",
    hour: "2-digit",
    minute: "2-digit",
  });
}

/**
 * A Date as YYYY-MM-DD in the VIEWER'S calendar.
 *
 * `toISOString().slice(0, 10)` is the trap this replaces: `new Date()` is local but
 * `toISOString()` converts to UTC, so the two disagree for the offset's worth of hours
 * every day. These strings filter BUSINESS dates -- Bill Date, Accounting Date -- which
 * are calendar dates in the utility's own timezone, never UTC instants. The same defect
 * was fixed on the backend in api/reporting_dates.py; fixing it there and leaving it
 * here would only have moved the disagreement to the client.
 *
 * Two copies of defaultDateRangeYtd/LastMonth lived here, byte-identical to the ones in
 * api.ts and imported by nobody -- every consumer takes them from @/lib/api. They are
 * deleted rather than fixed twice; this helper is what api.ts now builds them from.
 */
export function localIsoDate(d: Date): string {
  const month = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${month}-${day}`;
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
